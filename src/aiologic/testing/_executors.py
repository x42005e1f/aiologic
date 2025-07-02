#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys
import threading

from concurrent.futures import Executor, Future
from contextvars import ContextVar, copy_context
from functools import partial
from inspect import iscoroutinefunction
from typing import TYPE_CHECKING, TypeVar, overload

import aiologic

from aiologic.lowlevel._threads import _once as once

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

if TYPE_CHECKING:
    if sys.version_info >= (3, 9):
        from collections.abc import Awaitable, Callable
    else:
        from typing import Awaitable, Callable

_T = TypeVar("_T")
_P = ParamSpec("_P")


class _WorkItem:
    __slots__ = (
        "_args",
        "_func",
        "_future",
        "_kwargs",
    )

    def __init__(
        self,
        future: Future[_T],
        func: Callable[_P, _T],
        /,
        *args: _P.args,
        **kwargs: _P.kwargs,
    ) -> None:
        self._future = future

        self._func = func
        self._args = args
        self._kwargs = kwargs

    def is_async(self, /) -> bool:
        return iscoroutinefunction(self._func)

    async def async_run(self, /) -> None:
        if not self._future.set_running_or_notify_cancel():
            return

        try:
            result = await self._func(*self._args, **self._kwargs)
        except BaseException as exc:  # noqa: BLE001
            self._future.set_exception(exc)
            self = None  # noqa: PLW0642
        else:
            self._future.set_result(result)

    def green_run(self, /) -> None:
        if not self._future.set_running_or_notify_cancel():
            return

        try:
            result = self._func(*self._args, **self._kwargs)
        except BaseException as exc:  # noqa: BLE001
            self._future.set_exception(exc)
            self = None  # noqa: PLW0642
        else:
            self._future.set_result(result)

    def add_done_callback(self, func: Callable[[], object], /) -> None:
        self._future.add_done_callback(lambda _: func())

    def cancel(self, /) -> None:
        self._future.cancel()


class _TaskExecutor(Executor):
    __slots__ = (
        "_backend",
        "_library",
        "_shutdown",
        "_shutdown_lock",
        "_work_queue",
        "_work_thread",
    )

    def __init__(self, /, library: str, backend: str) -> None:
        self._backend = backend
        self._library = library

        self._shutdown = False
        self._shutdown_lock = threading.Lock()

        self._work_queue = aiologic.SimpleQueue()
        self._work_thread = None

    @overload
    def submit(
        self,
        fn: Callable[_P, Awaitable[_T]],
        /,
        *args: _P.args,
        **kwargs: _P.kwargs,
    ) -> Future[_T]: ...
    @overload
    def submit(
        self,
        fn: Callable[_P, _T],
        /,
        *args: _P.args,
        **kwargs: _P.kwargs,
    ) -> Future[_T]: ...
    def submit(self, fn, /, *args, **kwargs):
        with self._shutdown_lock:
            if self._shutdown:
                msg = "cannot schedule new futures after shutdown"
                raise RuntimeError(msg)

            if self._work_thread is None:
                self._work_thread = threading.Thread(target=self._run)
                self._work_thread.start()

            future = Future()

            self._work_queue.put(_WorkItem(future, fn, *args, **kwargs))

            return future

    if sys.version_info < (3, 9):
        _submit = submit

        @overload
        def submit(
            self,
            fn: Callable[_P, Awaitable[_T]],
            *args: _P.args,
            **kwargs: _P.kwargs,
        ) -> Future[_T]: ...
        @overload
        def submit(
            self,
            fn: Callable[_P, _T],
            *args: _P.args,
            **kwargs: _P.kwargs,
        ) -> Future[_T]: ...
        def submit(self, fn, *args, **kwargs):
            return self._submit(fn, *args, **kwargs)

    def shutdown(
        self,
        wait: bool = True,
        *,
        cancel_futures: bool = False,
    ) -> None:
        with self._shutdown_lock:
            self._shutdown = True

            if cancel_futures:
                while True:
                    try:
                        work_item = self._work_queue.green_get(blocking=False)
                    except aiologic.QueueEmpty:
                        break

                    if work_item is not None:
                        work_item.cancel()

            self._work_queue.put(None)

        if wait:
            if self._work_thread is not None:
                self._work_thread.join()

    def _run(self, /) -> None:
        raise NotImplementedError

    @property
    def backend(self, /) -> str:
        return self._backend

    @property
    def library(self, /) -> str:
        return self._library


class _ExecutorLocal(threading.local):
    executor: _TaskExecutor | None = None


_executor_tlocal: _ExecutorLocal = _ExecutorLocal()
_executor_cvar: ContextVar[_TaskExecutor | None] = ContextVar(
    "_executor_cvar",
    default=None,
)


@once
def _get_threading_executor_class() -> type[_TaskExecutor]:
    class _ThreadingExecutor(_TaskExecutor):
        __slots__ = ()

        def _run(self, /) -> None:
            _executor_tlocal.executor = self

            token = _executor_cvar.set(self)

            try:
                threads = set()

                while True:
                    work_item = self._work_queue.green_get()

                    if work_item is None:
                        break

                    thread = threading.Thread(
                        target=copy_context().run,
                        args=[work_item.green_run],
                    )
                    threads.add(thread)
                    work_item.add_done_callback(
                        partial(threads.discard, thread)
                    )
                    thread.start()

                while threads:
                    try:
                        thread = threads.pop()
                    except KeyError:
                        break
                    else:
                        thread.join()
            finally:
                _executor_cvar.reset(token)

                del _executor_tlocal.executor

    return _ThreadingExecutor


@once
def _get_eventlet_executor_class() -> type[_TaskExecutor]:
    import eventlet
    import eventlet.greenpool
    import eventlet.hubs

    class _EventletExecutor(_TaskExecutor):
        __slots__ = ()

        def _run(self, /) -> None:
            _executor_tlocal.executor = self

            token = _executor_cvar.set(self)

            try:
                try:
                    pool = eventlet.greenpool.GreenPool()

                    while True:
                        work_item = self._work_queue.green_get()

                        if work_item is None:
                            break

                        pool.spawn(copy_context().run, work_item.green_run)

                    pool.waitall()
                finally:
                    hub = eventlet.hubs.get_hub()

                    if hasattr(hub, "destroy"):
                        hub.destroy()
            finally:
                _executor_cvar.reset(token)

                del _executor_tlocal.executor

    return _EventletExecutor


@once
def _get_gevent_executor_class() -> type[_TaskExecutor]:
    import gevent
    import gevent.pool

    class _GeventExecutor(_TaskExecutor):
        __slots__ = ()

        def _run(self, /) -> None:
            _executor_tlocal.executor = self

            token = _executor_cvar.set(self)

            try:
                try:
                    pool = gevent.pool.Pool()

                    while True:
                        work_item = self._work_queue.green_get()

                        if work_item is None:
                            break

                        pool.spawn(copy_context().run, work_item.green_run)

                    pool.join()
                finally:
                    hub = gevent.get_hub()

                    if hasattr(hub, "destroy"):
                        hub.destroy()
            finally:
                _executor_cvar.reset(token)

                del _executor_tlocal.executor

    return _GeventExecutor


@once
def _get_asyncio_executor_class() -> type[_TaskExecutor]:
    import asyncio

    class _AsyncioExecutor(_TaskExecutor):
        __slots__ = ()

        def _run(self, /) -> None:
            asyncio.run(self._listen())

        async def _listen(self, /) -> None:
            _executor_tlocal.executor = self

            token = _executor_cvar.set(self)

            try:
                tasks = set()

                while True:
                    work_item = await self._work_queue.async_get()

                    if work_item is None:
                        break

                    if work_item.is_async():
                        task = asyncio.create_task(work_item.async_run())
                        tasks.add(task)
                        task.add_done_callback(tasks.discard)
                    else:
                        work_item.green_run()

                await asyncio.gather(*tasks)
            finally:
                _executor_cvar.reset(token)

                del _executor_tlocal.executor

    return _AsyncioExecutor


@once
def _get_curio_executor_class() -> type[_TaskExecutor]:
    import curio
    import curio.task

    class _CurioExecutor(_TaskExecutor):
        __slots__ = ()

        def _run(self, /) -> None:
            curio.run(self._listen, taskcls=curio.task.ContextTask)

        async def _listen(self, /) -> None:
            _executor_tlocal.executor = self

            token = _executor_cvar.set(self)

            try:
                async with curio.TaskGroup() as g:
                    while True:
                        work_item = await self._work_queue.async_get()

                        if work_item is None:
                            break

                        if work_item.is_async():
                            await g.spawn(work_item.async_run)
                        else:
                            work_item.green_run()
            finally:
                _executor_cvar.reset(token)

                del _executor_tlocal.executor

    return _CurioExecutor


@once
def _get_trio_executor_class() -> type[_TaskExecutor]:
    import trio

    class _TrioExecutor(_TaskExecutor):
        __slots__ = ()

        def _run(self, /) -> None:
            trio.run(self._listen)

        async def _listen(self, /) -> None:
            _executor_tlocal.executor = self

            token = _executor_cvar.set(self)

            try:
                async with trio.open_nursery() as nursery:
                    while True:
                        work_item = await self._work_queue.async_get()

                        if work_item is None:
                            break

                        if work_item.is_async():
                            nursery.start_soon(work_item.async_run)
                        else:
                            work_item.green_run()
            finally:
                _executor_cvar.reset(token)

                del _executor_tlocal.executor

    return _TrioExecutor


def _create_threading_executor(library: str, backend: str) -> _TaskExecutor:
    global _create_threading_executor

    _create_threading_executor = _get_threading_executor_class()

    return _create_threading_executor(library, backend)


def _create_eventlet_executor(library: str, backend: str) -> _TaskExecutor:
    global _create_eventlet_executor

    _create_eventlet_executor = _get_eventlet_executor_class()

    return _create_eventlet_executor(library, backend)


def _create_gevent_executor(library: str, backend: str) -> _TaskExecutor:
    global _create_gevent_executor

    _create_gevent_executor = _get_gevent_executor_class()

    return _create_gevent_executor(library, backend)


def _create_asyncio_executor(library: str, backend: str) -> _TaskExecutor:
    global _create_asyncio_executor

    _create_asyncio_executor = _get_asyncio_executor_class()

    return _create_asyncio_executor(library, backend)


def _create_curio_executor(library: str, backend: str) -> _TaskExecutor:
    global _create_curio_executor

    _create_curio_executor = _get_curio_executor_class()

    return _create_curio_executor(library, backend)


def _create_trio_executor(library: str, backend: str) -> _TaskExecutor:
    global _create_trio_executor

    _create_trio_executor = _get_trio_executor_class()

    return _create_trio_executor(library, backend)


def create_executor(library: str, backend: str | None = None) -> _TaskExecutor:
    if backend is None:
        backend = library

    if backend == "threading":
        if library != "threading":
            msg = f"unsupported library {library!r}"
            raise ValueError(msg)

        return _create_threading_executor(library, backend)

    if backend == "eventlet":
        if library != "eventlet":
            msg = f"unsupported library {library!r}"
            raise ValueError(msg)

        return _create_eventlet_executor(library, backend)

    if backend == "gevent":
        if library != "gevent":
            msg = f"unsupported library {library!r}"
            raise ValueError(msg)

        return _create_gevent_executor(library, backend)

    if backend == "asyncio":
        if library != "asyncio" and library != "anyio":
            msg = f"unsupported library {library!r}"
            raise ValueError(msg)

        return _create_asyncio_executor(library, backend)

    if backend == "curio":
        if library != "curio":
            msg = f"unsupported library {library!r}"
            raise ValueError(msg)

        return _create_curio_executor(library, backend)

    if backend == "trio":
        if library != "trio" and library != "anyio":
            msg = f"unsupported library {library!r}"
            raise ValueError(msg)

        return _create_trio_executor(library, backend)

    msg = f"unsupported backend {backend!r}"
    raise ValueError(msg)


def current_executor() -> _TaskExecutor:
    if (executor := _executor_tlocal.executor) is not None:
        return executor

    if (executor := _executor_cvar.get()) is not None:
        return executor

    msg = "no current executor"
    raise RuntimeError(msg)
