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
import aiologic._testing

if sys.version_info >= (3, 11):
    WaitTimeout = TimeoutError
else:
    from concurrent.futures import TimeoutError as WaitTimeout


def _spawn_decorator(func):
    @wraps(func)
    def wrapper(*args, spawn, **kwargs):
        return spawn(func, *args, spawn=spawn, **kwargs).wait()

    return wrapper


@pytest.fixture(scope="session")
def spawn(request):
    library, _, backend = request.param.partition("+")

    if not backend:
        backend = library

    if backend == "eventlet":  # see python-trio/trio#3015
        try:
            import trio  # noqa: F401
        except ImportError:
            pass

    pytest.importorskip(backend)
    pytest.importorskip(library)

    exec1 = aiologic._testing.create_executor(library, backend)
    exec2 = aiologic._testing.create_executor(library, backend)

    with exec1, exec2:

        def _spawn(func, /, *args, separate=False, **kwargs):
            if not separate:
                future = exec1.submit(func, *args, **kwargs)
            else:
                future = exec2.submit(func, *args, **kwargs)

            return aiologic._testing.Result(future)

        _spawn.backend = backend
        _spawn.library = library

        yield _spawn


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
            outer_future = Future()
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

            yield aiologic._testing.Result(outer_future)
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
            metafunc.parametrize(
                "spawn",
                [
                    "+".join(pair) if pair[0] != pair[1] else pair[0]
                    for pair in aiologic._testing.ASYNC_PAIRS
                ],
                indirect=True,
            )
        else:
            metafunc.parametrize(
                "spawn",
                [
                    "+".join(pair) if pair[0] != pair[1] else pair[0]
                    for pair in aiologic._testing.GREEN_PAIRS
                ],
                indirect=True,
            )


def pytest_collection_modifyitems(config, items):
    directory = Path(__file__).parent
    ordered_tests = defaultdict(
        partial(defaultdict, list),
        {
            "test_builtins": defaultdict(list),
            "test_collections": defaultdict(list),
            "test_itertools": defaultdict(list),
            "aiologic.lowlevel.test_markers": defaultdict(list),
            "aiologic.lowlevel.test_threads": defaultdict(list),
            "aiologic.lowlevel.test_libraries": defaultdict(list),
            "aiologic.lowlevel.test_ident": defaultdict(list),
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
