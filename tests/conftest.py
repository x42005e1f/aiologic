#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: 0BSD

import inspect
import sys

from collections import defaultdict
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from functools import partial, wraps
from itertools import chain
from pathlib import Path

import pytest

from wrapt import decorator

import aiologic

if sys.version_info >= (3, 11):
    WaitTimeout = TimeoutError
else:
    from concurrent.futures import TimeoutError as WaitTimeout

GREEN_LIBRARIES = ("threading", "eventlet", "gevent")
ASYNC_LIBRARIES = ("asyncio", "curio", "trio", "anyio+asyncio", "anyio+trio")


class _AwaitableFuture(Future):
    def __init__(self):
        super().__init__()

        self._async_event = aiologic.lowlevel.create_async_event()
        self._green_event = aiologic.lowlevel.create_green_event()

        self.add_done_callback(lambda _: self._async_event.set())
        self.add_done_callback(lambda _: self._green_event.set())

    def __await__(self):
        success = yield from self._async_event.__await__()

        if not success:
            raise WaitTimeout

        return self.result()

    def wait(self, timeout=None):
        success = self._green_event.wait(timeout)

        if not success:
            raise WaitTimeout

        return self.result()


def _spawn_decorator(func):
    @wraps(func)
    def wrapper(*args, spawn, **kwargs):
        return spawn(func, *args, spawn=spawn, **kwargs).result()

    return wrapper


@pytest.fixture(scope="session")
def spawn(request):
    library, _, backend = request.param.partition("+")

    if not backend:
        backend = library

    if backend == "eventlet":  # see python-trio/trio#3015
        try:
            import trio
        except ImportError:
            pass

    pytest.importorskip(backend)
    pytest.importorskip(library)

    with ThreadPoolExecutor(1) as executor:
        queue = aiologic.SimpleQueue()

        def _spawn(func, /, *args, **kwargs):
            future = _AwaitableFuture()

            queue.put((future, func, args, kwargs))

            return future

        if request.param in GREEN_LIBRARIES:

            def _run(future, func, args, kwargs):
                if future.set_running_or_notify_cancel():
                    try:
                        future.set_result(func(*args, **kwargs))
                    except BaseException as exc:  # noqa: BLE001
                        future.set_exception(exc)

            if library == "threading":
                import threading

                def _listen():
                    while (item := queue.green_get()) is not None:
                        threading.Thread(target=_run, args=item).start()

                future = executor.submit(_listen)
            elif library == "eventlet":
                import eventlet
                import eventlet.greenpool
                import eventlet.hubs

                def _listen():
                    try:
                        pool = eventlet.greenpool.GreenPool()

                        while (item := queue.green_get()) is not None:
                            pool.spawn(_run, *item)

                        pool.waitall()
                    finally:
                        hub = eventlet.hubs.get_hub()

                        if hasattr(hub, "destroy"):
                            hub.destroy()

                future = executor.submit(_listen)
            elif library == "gevent":
                import gevent
                import gevent.pool

                def _listen():
                    try:
                        pool = gevent.pool.Pool()

                        while (item := queue.green_get()) is not None:
                            pool.spawn(_run, *item)

                        pool.join()
                    finally:
                        hub = gevent.get_hub()

                        if hasattr(hub, "destroy"):
                            hub.destroy()

                future = executor.submit(_listen)
        elif request.param in ASYNC_LIBRARIES:

            async def _run(future, func, args, kwargs):
                if future.set_running_or_notify_cancel():
                    try:
                        future.set_result(await func(*args, **kwargs))
                    except BaseException as exc:  # noqa: BLE001
                        future.set_exception(exc)

            if library == "asyncio":
                import asyncio

                async def _listen():
                    tasks = set()

                    while (item := await queue.async_get()) is not None:
                        task = asyncio.create_task(_run(*item))
                        tasks.add(task)
                        task.add_done_callback(tasks.discard)

                    await asyncio.gather(*tasks)

                future = executor.submit(asyncio.run, _listen())
            elif library == "curio":
                import curio

                async def _listen():
                    async with curio.TaskGroup() as g:
                        while (item := await queue.async_get()) is not None:
                            await g.spawn(_run, *item)

                future = executor.submit(curio.run, _listen)
            elif library == "trio":
                import trio

                async def _listen():
                    async with trio.open_nursery() as nursery:
                        while (item := await queue.async_get()) is not None:
                            nursery.start_soon(_run, *item)

                future = executor.submit(trio.run, _listen)
            elif library == "anyio":
                import anyio

                async def _listen():
                    async with anyio.create_task_group() as tg:
                        while (item := await queue.async_get()) is not None:
                            tg.start_soon(_run, *item)

                future = executor.submit(anyio.run, _listen, backend=backend)

        _spawn.backend = backend
        _spawn.library = library

        try:
            yield _spawn
        finally:
            queue.put(None)

            future.result()


@contextmanager
def _test_thread_safety_cm(event, *functions):
    with ThreadPoolExecutor(len(functions) + 1) as executor:
        barrier = aiologic.Latch(len(functions) + 1)
        stopped = aiologic.Flag()

        @decorator
        async def _async_wrapper(wrapped, instance, args, kwargs):
            await barrier

            if "stopped" in inspect.signature(wrapped).parameters:
                while True:
                    result = await wrapped(*args, stopped=stopped, **kwargs)

                    if stopped:
                        break
            else:
                while True:
                    result = await wrapped(*args, **kwargs)

                    if stopped:
                        break

            return result

        @decorator
        def _green_wrapper(wrapped, instance, args, kwargs):
            barrier.wait()

            if "stopped" in inspect.signature(wrapped).parameters:
                while True:
                    result = wrapped(*args, stopped=stopped, **kwargs)

                    if stopped:
                        break
            else:
                while True:
                    result = wrapped(*args, **kwargs)

                    if stopped:
                        break

            return result

        interval = sys.getswitchinterval()
        sys.setswitchinterval(min(1e-6, interval))

        try:
            outer_future = _AwaitableFuture()
            inner_futures = {
                (  # functools.partial(spawn, ...)
                    f.func(
                        _async_wrapper(f.args[0]),
                        *f.args[1:],
                        **f.keywords,
                    )
                    if inspect.iscoroutinefunction(f.args[0])
                    else f.func(
                        _green_wrapper(f.args[0]),
                        *f.args[1:],
                        **f.keywords,
                    )
                )
                if hasattr(getattr(f, "func", None), "backend")
                else executor.submit(_green_wrapper(f))
                for f in functions
            }

            @executor.submit
            def _wait():
                try:
                    barrier.wait()

                    for future in as_completed(inner_futures, timeout=6):
                        future.result()  # reraise
                except WaitTimeout:
                    outer_future.set_result(True)
                except BaseException as exc:  # noqa: BLE001
                    outer_future.set_exception(exc)
                else:
                    outer_future.set_result(False)
                finally:
                    stopped.set()

            yield outer_future
        finally:
            sys.setswitchinterval(interval)


@pytest.fixture
def test_thread_safety(request):
    if inspect.iscoroutinefunction(request.function) or (
        hasattr(request.function, "__wrapped__")
        and inspect.iscoroutinefunction(request.function.__wrapped__)
    ):

        async def _impl(*args):
            with _test_thread_safety_cm(*args) as future:
                return await future

    else:

        def _impl(*args):
            with _test_thread_safety_cm(*args) as future:
                return future.wait()

    return _impl


def pytest_addoption(parser):
    parser.addoption(
        "--thread-safety",
        action="store_true",
        default=False,
        help="run thread-safety tests",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "threadsafe: mark test as thread-safety test",
    )


def pytest_generate_tests(metafunc):
    if "spawn" in metafunc.fixturenames:
        if inspect.iscoroutinefunction(metafunc.function):
            metafunc.parametrize("spawn", ASYNC_LIBRARIES, indirect=True)
        else:
            metafunc.parametrize("spawn", GREEN_LIBRARIES, indirect=True)


def pytest_collection_modifyitems(config, items):
    directory = Path(__file__).parent
    ordered_tests = defaultdict(
        partial(defaultdict, list),
        {
            "test_builtins": defaultdict(list),
            "test_collections": defaultdict(list),
            "test_itertools": defaultdict(list),
            "aiologic.lowlevel.test_markers": defaultdict(list),
            "aiologic.lowlevel.test_libraries": defaultdict(list),
            "aiologic.test_flags": defaultdict(list),
        },
    )

    for item in items:
        module_name = ".".join(item.path.relative_to(directory).parts)[:-3]
        ordered_tests[module_name][item.obj].append(item)

        if "spawn" in item.fixturenames:
            item.obj = _spawn_decorator(item.obj)

        if "test_thread_safety" in item.fixturenames:
            item.add_marker(pytest.mark.threadsafe)

        if "threadsafe" in item.keywords:
            if not config.getoption("--thread-safety"):
                item.add_marker(
                    pytest.mark.skip(
                        reason="need --thread-safety option to run",
                    )
                )

    items[:] = chain.from_iterable(
        chain.from_iterable(mapping.values())
        for mapping in ordered_tests.values()
    )
