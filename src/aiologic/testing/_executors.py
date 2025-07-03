#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys
import threading

from abc import ABC, abstractmethod
from concurrent.futures import (
    BrokenExecutor,
    Executor,
    Future,
    InvalidStateError,
)
from functools import partial
from inspect import iscoroutinefunction
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    NoReturn,
    TypeVar,
    final,
    overload,
)

import aiologic

from aiologic.lowlevel._threads import _once as once
from aiologic.lowlevel._utils import _external as external

if sys.version_info >= (3, 11):
    from typing import TypeVarTuple, Unpack
else:
    from typing_extensions import TypeVarTuple, Unpack

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

if TYPE_CHECKING:
    if sys.version_info >= (3, 9):
        from collections.abc import Callable, Coroutine
    else:
        from typing import Callable, Coroutine

_T = TypeVar("_T")
_Ts = TypeVarTuple("_Ts")
_P = ParamSpec("_P")


class _ExecutorLocal(threading.local):
    executor: TaskExecutor | None = None


_executor_tlocal: _ExecutorLocal = _ExecutorLocal()


@final
class _WorkItem(Generic[_T]):
    __slots__ = (
        "_args",
        "_func",
        "_future",
        "_kwargs",
        "_new_task",
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

        self._new_task = False

    def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn:
        bcs = _WorkItem
        bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

        msg = f"type '{bcs_repr}' is not an acceptable base type"
        raise TypeError(msg)

    def __reduce__(self, /) -> NoReturn:
        msg = f"cannot reduce {self!r}"
        raise TypeError(msg)

    async def async_run(self, /) -> None:
        if not self._future.set_running_or_notify_cancel():
            return

        try:
            result = self._func(*self._args, **self._kwargs)

            if iscoroutinefunction(self._func):
                result = await result
        except BaseException as exc:
            try:
                self._future.set_exception(exc)
            except InvalidStateError:
                pass
            else:
                self = None  # noqa: PLW0642
                return

            raise
        else:
            try:
                self._future.set_result(result)
            except InvalidStateError:
                pass

    def green_run(self, /, executor: TaskExecutor | None = None) -> None:
        if not self._future.set_running_or_notify_cancel():
            return

        if executor is not None:
            _executor_tlocal.executor = executor

        try:
            result = self._func(*self._args, **self._kwargs)

            if iscoroutinefunction(self._func):
                msg = f"a green function was expected, got {self._func!r}"
                raise TypeError(msg)
        except BaseException as exc:
            try:
                self._future.set_exception(exc)
            except InvalidStateError:
                pass
            else:
                self = None  # noqa: PLW0642
                return

            raise
        else:
            try:
                self._future.set_result(result)
            except InvalidStateError:
                pass
        finally:
            if executor is not None:
                del _executor_tlocal.executor

    def add_done_callback(self, func: Callable[[], object], /) -> None:
        self._future.add_done_callback(lambda _: func())

    def cancel(self, /) -> None:
        self._future.cancel()

    def abort(self, /, cause: BaseException) -> None:
        exc = BrokenExecutor()
        exc.__cause__ = cause

        try:
            self._future.set_exception(exc)
        except InvalidStateError:
            pass

    @property
    def future(self, /) -> Future[_T]:
        return self._future

    @property
    def new_task(self, /) -> bool:
        return self._new_task

    @new_task.setter
    def new_task(self, /, value: bool) -> None:
        self._new_task = value


class TaskExecutor(Executor, ABC):
    __slots__ = (
        "_backend",
        "_backend_options",
        "_broken_by",
        "_library",
        "_shutdown",
        "_shutdown_lock",
        "_work_items",
        "_work_queue",
        "_work_thread",
    )

    def __init__(
        self,
        /,
        library: str,
        backend: str,
        backend_options: dict[str, Any],
    ) -> None:
        self._backend = backend
        self._backend_options = backend_options
        self._library = library

        self._shutdown = False
        self._shutdown_lock = threading.RLock()

        self._work_items = set()
        self._work_queue = aiologic.SimpleQueue()
        self._work_thread = None

        self._broken_by = None

    def __repr__(self, /) -> str:
        cls = self.__class__
        if cls.__module__ == __name__:
            cls = TaskExecutor
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        args = [repr(self._library), repr(self._backend)]

        if self._backend_options:
            args.append(f"backend_options={self._backend_options!r}")

        object_repr = f"{cls_repr}({', '.join(args)})"

        if self._broken_by is not None:
            extra = "broken"
        elif self._shutdown:
            extra = "shutdown"
        elif self._work_thread is not None:
            extra = f"running, tasks={len(self._work_items)}"
        else:
            extra = "pending"

        return f"<{object_repr} at {id(self):#x} [{extra}]>"

    @overload
    def _create_work_item(
        self,
        fn: Callable[_P, Coroutine[Any, Any, _T]],
        /,
        *args: _P.args,
        **kwargs: _P.kwargs,
    ) -> _WorkItem[_T]: ...
    @overload
    def _create_work_item(
        self,
        fn: Callable[_P, _T],
        /,
        *args: _P.args,
        **kwargs: _P.kwargs,
    ) -> _WorkItem[_T]: ...
    def _create_work_item(self, fn, /, *args, **kwargs):
        with self._shutdown_lock:
            if self._broken_by is not None:
                raise BrokenExecutor from self._broken_by

            if self._shutdown:
                msg = "cannot schedule new futures after shutdown"
                raise RuntimeError(msg)

            if self._work_thread is None:
                self._work_thread = threading.Thread(target=self._run)
                self._work_thread.start()

            future = Future()

            work_item = _WorkItem(future, fn, *args, **kwargs)
            self._work_items.add(work_item)
            work_item.add_done_callback(
                partial(
                    self._work_items.discard,
                    work_item,
                )
            )

            return work_item

    def _create_task(self, /, work_item: _WorkItem[Any]) -> None:
        self._work_queue.put(work_item)

    @overload
    def schedule(
        self,
        fn: Callable[_P, Coroutine[Any, Any, _T]],
        /,
        *args: _P.args,
        **kwargs: _P.kwargs,
    ) -> Future[_T]: ...
    @overload
    def schedule(
        self,
        fn: Callable[_P, _T],
        /,
        *args: _P.args,
        **kwargs: _P.kwargs,
    ) -> Future[_T]: ...
    def schedule(self, fn, /, *args, **kwargs):
        with self._shutdown_lock:
            work_item = self._create_work_item(fn, *args, **kwargs)

            self._work_queue.put(work_item)

            return work_item.future

    @overload
    def submit(
        self,
        fn: Callable[_P, Coroutine[Any, Any, _T]],
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
            work_item = self._create_work_item(fn, *args, **kwargs)
            work_item.new_task = True

            if current_executor(failsafe=True) is self:
                self._create_task(work_item)
            else:
                self._work_queue.put(work_item)

            return work_item.future

    if sys.version_info < (3, 9):
        _submit = submit

        @overload
        def submit(
            self,
            fn: Callable[_P, Coroutine[Any, Any, _T]],
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
                work_queue = self._work_queue

                while work_queue:
                    try:
                        work_item = work_queue.green_get(blocking=False)
                    except aiologic.QueueEmpty:
                        break
                    else:
                        if work_item is not None:
                            work_item.cancel()

            self._work_queue.put(None)

        if wait:
            if self._work_thread is not None:
                self._work_thread.join()

    def _abort(self, /, cause: BaseException) -> None:
        with self._shutdown_lock:
            self._broken_by = cause

            work_items = self._work_items
            work_queue = self._work_queue

            while work_queue:
                try:
                    work_queue.green_get(blocking=False)
                except aiologic.QueueEmpty:
                    break

            while work_items:
                try:
                    work_item = work_items.pop()
                except IndexError:
                    break
                else:
                    work_item.abort(cause)

    @abstractmethod
    def _run(self, /) -> None:
        raise NotImplementedError

    @property
    def backend(self, /) -> str:
        return self._backend

    @property
    def library(self, /) -> str:
        return self._library


@once
def _get_threading_executor_class() -> type[TaskExecutor]:
    @final
    class _ThreadingExecutor(TaskExecutor):
        __slots__ = ()

        def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn:
            bcs = _ThreadingExecutor
            bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

            msg = f"type '{bcs_repr}' is not an acceptable base type"
            raise TypeError(msg)

        def __reduce__(self, /) -> NoReturn:
            msg = f"cannot reduce {self!r}"
            raise TypeError(msg)

        def _run(self, /) -> None:
            try:
                self._apply_backend_options(**self._backend_options)
                self._listen()
            except BaseException as exc:  # noqa: BLE001
                self._abort(exc)
                self = None  # noqa: PLW0642

        def _apply_backend_options(self, /) -> None:
            pass

        def _listen(self, /) -> None:
            _executor_tlocal.executor = self

            try:
                no_checkpoints = aiologic.lowlevel.disable_checkpoints()

                threads = set()

                while True:
                    with no_checkpoints:
                        work_item = self._work_queue.green_get()

                    if work_item is None:
                        break

                    if work_item.new_task:
                        thread = threading.Thread(
                            target=work_item.green_run,
                            args=[self],
                        )
                        threads.add(thread)
                        work_item.add_done_callback(
                            partial(
                                threads.discard,
                                thread,
                            )
                        )
                        thread.start()
                    else:
                        work_item.green_run()

                while threads:
                    try:
                        thread = threads.pop()
                    except KeyError:
                        break
                    else:
                        thread.join()
            finally:
                try:
                    del _executor_tlocal.executor
                except AttributeError:
                    pass

                self = None  # noqa: PLW0642

    return _ThreadingExecutor


@once
def _get_eventlet_executor_class() -> type[TaskExecutor]:
    import eventlet
    import eventlet.greenpool
    import eventlet.hubs

    @final
    class _EventletExecutor(TaskExecutor):
        __slots__ = ("_work_pool",)

        def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn:
            bcs = _EventletExecutor
            bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

            msg = f"type '{bcs_repr}' is not an acceptable base type"
            raise TypeError(msg)

        def __reduce__(self, /) -> NoReturn:
            msg = f"cannot reduce {self!r}"
            raise TypeError(msg)

        def _run(self, /) -> None:
            try:
                self._apply_backend_options(**self._backend_options)
                self._listen()
            except BaseException as exc:  # noqa: BLE001
                self._abort(exc)
                self = None  # noqa: PLW0642

        def _apply_backend_options(self, /) -> None:
            pass

        def _create_task(self, /, work_item: _WorkItem[Any]) -> None:
            self._work_pool.spawn(work_item.green_run)

        def _listen(self, /) -> None:
            _executor_tlocal.executor = self

            try:
                try:
                    no_checkpoints = aiologic.lowlevel.disable_checkpoints()

                    self._work_pool = eventlet.greenpool.GreenPool()

                    while True:
                        with no_checkpoints:
                            work_item = self._work_queue.green_get()

                        if work_item is None:
                            break

                        if work_item.new_task:
                            self._create_task(work_item)
                        else:
                            work_item.green_run()

                    self._work_pool.waitall()
                finally:
                    hub = eventlet.hubs.get_hub()

                    if hasattr(hub, "destroy"):
                        hub.destroy()
            finally:
                try:
                    del _executor_tlocal.executor
                except AttributeError:
                    pass

                self = None  # noqa: PLW0642

    return _EventletExecutor


@once
def _get_gevent_executor_class() -> type[TaskExecutor]:
    import gevent
    import gevent.pool

    @final
    class _GeventExecutor(TaskExecutor):
        __slots__ = ("_work_pool",)

        def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn:
            bcs = _GeventExecutor
            bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

            msg = f"type '{bcs_repr}' is not an acceptable base type"
            raise TypeError(msg)

        def __reduce__(self, /) -> NoReturn:
            msg = f"cannot reduce {self!r}"
            raise TypeError(msg)

        def _run(self, /) -> None:
            try:
                self._apply_backend_options(**self._backend_options)
                self._listen()
            except BaseException as exc:  # noqa: BLE001
                self._abort(exc)
                self = None  # noqa: PLW0642

        def _apply_backend_options(self, /) -> None:
            pass

        def _create_task(self, /, work_item: _WorkItem[Any]) -> None:
            self._work_pool.spawn(work_item.green_run)

        def _listen(self, /) -> None:
            _executor_tlocal.executor = self

            try:
                try:
                    no_checkpoints = aiologic.lowlevel.disable_checkpoints()

                    self._work_pool = gevent.pool.Pool()

                    while True:
                        with no_checkpoints:
                            work_item = self._work_queue.green_get()

                        if work_item is None:
                            break

                        if work_item.new_task:
                            self._create_task(work_item)
                        else:
                            work_item.green_run()

                    self._work_pool.join()
                finally:
                    hub = gevent.get_hub()

                    if hasattr(hub, "destroy"):
                        hub.destroy()
            finally:
                try:
                    del _executor_tlocal.executor
                except AttributeError:
                    pass

                self = None  # noqa: PLW0642

    return _GeventExecutor


@once
def _get_asyncio_executor_class() -> type[TaskExecutor]:
    import asyncio

    @final
    class _AsyncioExecutor(TaskExecutor):
        __slots__ = ("_work_tasks",)

        def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn:
            bcs = _AsyncioExecutor
            bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

            msg = f"type '{bcs_repr}' is not an acceptable base type"
            raise TypeError(msg)

        def __reduce__(self, /) -> NoReturn:
            msg = f"cannot reduce {self!r}"
            raise TypeError(msg)

        def _run(self, /) -> None:
            try:
                asyncio.run(self._listen(), **self._backend_options)
            except BaseException as exc:  # noqa: BLE001
                self._abort(exc)
                self = None  # noqa: PLW0642

        def _create_task(self, /, work_item: _WorkItem[Any]) -> None:
            task = asyncio.create_task(work_item.async_run())
            self._work_tasks.add(task)
            task.add_done_callback(self._work_tasks.discard)

        async def _listen(self, /) -> None:
            _executor_tlocal.executor = self

            try:
                no_checkpoints = aiologic.lowlevel.disable_checkpoints()

                self._work_tasks = set()

                while True:
                    async with no_checkpoints:
                        work_item = await self._work_queue.async_get()

                    if work_item is None:
                        break

                    if work_item.new_task:
                        self._create_task(work_item)
                    else:
                        await work_item.async_run()

                await asyncio.gather(*self._work_tasks)
            finally:
                try:
                    del _executor_tlocal.executor
                except AttributeError:
                    pass

                self = None  # noqa: PLW0642

    return _AsyncioExecutor


@once
def _get_curio_executor_class() -> type[TaskExecutor]:
    import curio
    import curio.task

    @final
    class _CurioExecutor(TaskExecutor):
        __slots__ = ()

        def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn:
            bcs = _CurioExecutor
            bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

            msg = f"type '{bcs_repr}' is not an acceptable base type"
            raise TypeError(msg)

        def __reduce__(self, /) -> NoReturn:
            msg = f"cannot reduce {self!r}"
            raise TypeError(msg)

        def _run(self, /) -> None:
            try:
                curio.run(self._listen, **self._backend_options)
            except BaseException as exc:  # noqa: BLE001
                self._abort(exc)
                self = None  # noqa: PLW0642

        async def _listen(self, /) -> None:
            _executor_tlocal.executor = self

            try:
                no_checkpoints = aiologic.lowlevel.disable_checkpoints()

                async with curio.TaskGroup() as g:
                    while True:
                        async with no_checkpoints:
                            work_item = await self._work_queue.async_get()

                        if work_item is None:
                            break

                        if work_item.new_task:
                            await g.spawn(work_item.async_run)
                        else:
                            await work_item.async_run()
            finally:
                try:
                    del _executor_tlocal.executor
                except AttributeError:
                    pass

                self = None  # noqa: PLW0642

    return _CurioExecutor


@once
def _get_trio_executor_class() -> type[TaskExecutor]:
    import trio

    @final
    class _TrioExecutor(TaskExecutor):
        __slots__ = ("_work_nursery",)

        def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn:
            bcs = _TrioExecutor
            bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

            msg = f"type '{bcs_repr}' is not an acceptable base type"
            raise TypeError(msg)

        def __reduce__(self, /) -> NoReturn:
            msg = f"cannot reduce {self!r}"
            raise TypeError(msg)

        def _run(self, /) -> None:
            try:
                trio.run(self._listen, **self._backend_options)
            except BaseException as exc:  # noqa: BLE001
                self._abort(exc)
                self = None  # noqa: PLW0642

        def _create_task(self, /, work_item: _WorkItem[Any]) -> None:
            self._work_nursery.start_soon(work_item.async_run)

        async def _listen(self, /) -> None:
            _executor_tlocal.executor = self

            try:
                no_checkpoints = aiologic.lowlevel.disable_checkpoints()

                async with trio.open_nursery() as nursery:
                    self._work_nursery = nursery

                    while True:
                        async with no_checkpoints:
                            work_item = await self._work_queue.async_get()

                        if work_item is None:
                            break

                        if work_item.new_task:
                            self._create_task(work_item)
                        else:
                            await work_item.async_run()
            finally:
                try:
                    del _executor_tlocal.executor
                except AttributeError:
                    pass

                self = None  # noqa: PLW0642

    return _TrioExecutor


@once
def _get_anyio_executor_class() -> type[TaskExecutor]:
    import anyio

    @final
    class _AnyioExecutor(TaskExecutor):
        __slots__ = ("_work_task_group",)

        def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn:
            bcs = _AnyioExecutor
            bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

            msg = f"type '{bcs_repr}' is not an acceptable base type"
            raise TypeError(msg)

        def __reduce__(self, /) -> NoReturn:
            msg = f"cannot reduce {self!r}"
            raise TypeError(msg)

        def _run(self, /) -> None:
            try:
                anyio.run(
                    self._listen,
                    backend=self._backend,
                    backend_options=self._backend_options,
                )
            except BaseException as exc:  # noqa: BLE001
                self._abort(exc)
                self = None  # noqa: PLW0642

        def _create_task(self, /, work_item: _WorkItem[Any]) -> None:
            self._work_task_group.start_soon(work_item.async_run)

        async def _listen(self, /) -> None:
            _executor_tlocal.executor = self

            try:
                no_checkpoints = aiologic.lowlevel.disable_checkpoints()

                async with anyio.create_task_group() as tg:
                    self._work_task_group = tg

                    while True:
                        async with no_checkpoints:
                            work_item = await self._work_queue.async_get()

                        if work_item is None:
                            break

                        if work_item.new_task:
                            self._create_task(work_item)
                        else:
                            await work_item.async_run()
            finally:
                try:
                    del _executor_tlocal.executor
                except AttributeError:
                    pass

                self = None  # noqa: PLW0642

    return _AnyioExecutor


def _create_threading_executor(
    library: str,
    backend: str,
    backend_options: dict[str, Any],
) -> TaskExecutor:
    global _create_threading_executor

    _create_threading_executor = _get_threading_executor_class()

    return _create_threading_executor(library, backend, backend_options)


def _create_eventlet_executor(
    library: str,
    backend: str,
    backend_options: dict[str, Any],
) -> TaskExecutor:
    global _create_eventlet_executor

    _create_eventlet_executor = _get_eventlet_executor_class()

    return _create_eventlet_executor(library, backend, backend_options)


def _create_gevent_executor(
    library: str,
    backend: str,
    backend_options: dict[str, Any],
) -> TaskExecutor:
    global _create_gevent_executor

    _create_gevent_executor = _get_gevent_executor_class()

    return _create_gevent_executor(library, backend, backend_options)


def _create_asyncio_executor(
    library: str,
    backend: str,
    backend_options: dict[str, Any],
) -> TaskExecutor:
    global _create_asyncio_executor

    _create_asyncio_executor = _get_asyncio_executor_class()

    return _create_asyncio_executor(library, backend, backend_options)


def _create_curio_executor(
    library: str,
    backend: str,
    backend_options: dict[str, Any],
) -> TaskExecutor:
    global _create_curio_executor

    _create_curio_executor = _get_curio_executor_class()

    return _create_curio_executor(library, backend, backend_options)


def _create_trio_executor(
    library: str,
    backend: str,
    backend_options: dict[str, Any],
) -> TaskExecutor:
    global _create_trio_executor

    _create_trio_executor = _get_trio_executor_class()

    return _create_trio_executor(library, backend, backend_options)


def _create_anyio_executor(
    library: str,
    backend: str,
    backend_options: dict[str, Any],
) -> TaskExecutor:
    global _create_anyio_executor

    _create_anyio_executor = _get_anyio_executor_class()

    return _create_anyio_executor(library, backend, backend_options)


def create_executor(
    library: str,
    backend: str | None = None,
    backend_options: dict[str, Any] | None = None,
) -> TaskExecutor:
    if backend is None:
        if library == "anyio":
            backend = "asyncio"
        else:
            backend = library

    if backend_options is None:
        backend_options = {}

    impl = None

    if library == "threading":
        if backend == "threading":
            impl = _create_threading_executor
    elif library == "eventlet":
        if backend == "eventlet":
            impl = _create_eventlet_executor
    elif library == "gevent":
        if backend == "gevent":
            impl = _create_gevent_executor
    elif library == "asyncio":
        if backend == "asyncio":
            impl = _create_asyncio_executor
    elif library == "curio":
        if backend == "curio":
            impl = _create_curio_executor
    elif library == "trio":
        if backend == "trio":
            impl = _create_trio_executor
    elif library == "anyio":
        if backend == "asyncio" or backend == "trio":
            impl = _create_anyio_executor
    else:
        msg = f"unsupported library {library!r}"
        raise ValueError(msg)

    if impl is None:
        msg = f"unsupported backend {backend!r} for library {library!r}"
        raise ValueError(msg)

    return impl(library, backend, backend_options)


def current_executor(*, failsafe: bool = False) -> TaskExecutor:
    executor = _executor_tlocal.executor

    if executor is None and not failsafe:
        msg = "no current executor"
        raise RuntimeError(msg)

    return executor


@overload
@external
def run(
    func: Callable[[Unpack[_Ts]], Coroutine[Any, Any, _T]],
    /,
    *args: Unpack[_Ts],
    library: str | None = None,
    backend: str | None = None,
    backend_options: dict[str, Any] | None = None,
) -> _T: ...
@overload
@external
def run(
    func: Callable[[Unpack[_Ts]], _T],
    /,
    *args: Unpack[_Ts],
    library: str | None = None,
    backend: str | None = None,
    backend_options: dict[str, Any] | None = None,
) -> _T: ...
def run(func, /, *args, library=None, backend=None, backend_options=None):
    if library is None:
        if backend is None:
            library = backend = "asyncio"
        else:
            library = backend

    with create_executor(library, backend, backend_options) as executor:
        return executor.submit(func, *args).result()
