#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from abc import ABC, abstractmethod
from concurrent.futures import BrokenExecutor, Future
from contextvars import copy_context
from inspect import isawaitable, iscoroutinefunction
from typing import TYPE_CHECKING, Any, NoReturn, TypeVar, final

from aiologic.lowlevel import (
    async_checkpoint,
    create_async_event,
    create_green_event,
    green_checkpoint,
    once,
)
from aiologic.meta import DEFAULT, DefaultType

from ._exceptions import (
    _CancelledError,
    _TimeoutError,
    get_cancelled_exc_class,
    get_timeout_exc_class,
)
from ._executors import TaskExecutor, current_executor
from ._results import FALSE_RESULT, TRUE_RESULT, Result

if sys.version_info >= (3, 11):
    from typing import TypeVarTuple, Unpack, overload
else:
    from typing_extensions import TypeVarTuple, Unpack, overload

if TYPE_CHECKING:
    if sys.version_info >= (3, 9):
        from collections.abc import Awaitable, Callable, Coroutine, Generator
    else:
        from typing import Awaitable, Callable, Coroutine, Generator

_T = TypeVar("_T")
_Ts = TypeVarTuple("_Ts")


class TaskCancelled(BaseException):
    def __init__(self, /, task: Task[object]) -> None:
        super().__init__()

        self._task = task

    @property
    def task(self, /) -> Task[object]:
        return self._task


class Task(Result[_T], ABC):
    __slots__ = (
        "_args",
        "_cancelled",
        "_cancelled_after_start",
        "_done",
        "_executor",
        "_func",
        "_started",
    )

    @overload
    def __init__(
        self,
        func: Awaitable[_T],
        /,
        *,
        executor: TaskExecutor,
    ) -> None: ...
    @overload
    def __init__(
        self,
        func: Callable[[Unpack[_Ts]], Coroutine[Any, Any, _T]],
        /,
        *args: Unpack[_Ts],
        executor: TaskExecutor,
    ) -> None: ...
    @overload
    def __init__(
        self,
        func: Callable[[Unpack[_Ts]], _T],
        /,
        *args: Unpack[_Ts],
        executor: TaskExecutor,
    ) -> None: ...
    def __init__(self, func, /, *args, executor):
        self._func = func
        self._args = args
        self._executor = executor

        self._done = Result(Future())
        self._cancelled = Result(Future())
        self._cancelled_after_start = False
        self._started = Result(Future())

        future = self._executor._submit_with_context(self._run, copy_context())
        future.add_done_callback(self._callback)

        super().__init__(future)

    def __repr__(self, /) -> str:
        cls = self.__class__
        if cls.__module__ == __name__:
            cls = Task
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        if isawaitable(self._func):
            args = [repr(self._func)]
        else:
            args = [self._func.__name__]
            args.extend(map(repr, self._args))

        executor = self._executor

        if executor.library != executor.backend:
            args.append(f"executor=<{executor.library}+{executor.backend}>")
        else:
            args.append(f"executor=<{executor.library}>")

        object_repr = f"{cls_repr}({', '.join(args)})"

        if self._future.running():
            extra = "running"
        elif self._future.done():
            if self._future.cancelled():
                extra = "cancelled"
            elif isinstance(self._future.exception(), _CancelledError):
                extra = "cancelled"
            elif isinstance(self._future.exception(), BrokenExecutor):
                extra = "aborted"
            else:
                extra = "finished"
        else:
            extra = "pending"

        return f"<{object_repr} at {id(self):#x} [{extra}]>"

    def __bool__(self, /) -> bool:
        return self._future.running()

    def __await__(self) -> Generator[Any, Any, _T]:
        if not self._future.done():
            event = create_async_event()
            self._future.add_done_callback(lambda _: event.set())

            try:
                success = yield from event.__await__()
            finally:
                if event.cancelled():
                    event = create_async_event(shield=True)

                    if not self._future.done():
                        self.cancel()

                        yield from event.__await__()

            if not success:
                raise get_timeout_exc_class(failback=_TimeoutError)
        else:
            yield from async_checkpoint().__await__()

        try:
            return self._future.result()
        except _CancelledError as exc:
            raise TaskCancelled(self) from exc.__cause__
        finally:
            self = None  # noqa: PLW0642

    def wait(self, timeout: float | None = None) -> _T:
        if not self._future.done():
            event = create_green_event()
            self._future.add_done_callback(lambda _: event.set())

            try:
                success = event.wait(timeout)
            finally:
                if event.cancelled():
                    event = create_green_event(shield=True)

                    if not self._future.done():
                        self.cancel()

                        event.wait()

            if not success:
                raise get_timeout_exc_class(failback=_TimeoutError)
        else:
            green_checkpoint()

        try:
            return self._future.result()
        except _CancelledError as exc:
            raise TaskCancelled(self) from exc.__cause__
        finally:
            self = None  # noqa: PLW0642

    def cancel(self, /) -> Result[bool]:
        if self._future.cancel():
            return TRUE_RESULT

        if self._future.done():
            if self._cancelled_after_start:
                return TRUE_RESULT
            else:
                return FALSE_RESULT

        try:
            return Result(self._executor.schedule(self._cancel))
        except RuntimeError:  # executor is shutdown or broken
            return self._cancelled

    def cancelled(self, /) -> Result[bool]:
        if self._future.done():
            if self._cancelled_after_start or self._future.cancelled():
                return TRUE_RESULT
            else:
                return FALSE_RESULT

        return self._cancelled

    def running(self, /) -> Result[bool]:
        if self._future.running():
            return TRUE_RESULT

        if self._future.done():
            return FALSE_RESULT

        return self._started

    def done(self, /) -> Result[bool]:
        if self._future.done():
            return TRUE_RESULT

        return self._done

    def _callback(self, /, future: Future[_T]) -> None:
        if not self._started.future.done():
            self._started.future.set_result(False)

        self._cancelled.future.set_result(
            self._cancelled_after_start or future.cancelled()
        )
        self._done.future.set_result(True)

    @abstractmethod
    def _run(self, /) -> Coroutine[Any, Any, _T] | _T:
        raise NotImplementedError

    @abstractmethod
    def _cancel(self, /) -> Coroutine[Any, Any, bool] | bool:
        raise NotImplementedError

    @property
    def executor(self, /) -> TaskExecutor:
        return self._executor


@once
def _get_threading_task_class() -> type[Task[_T]]:
    @final
    class _ThreadingTask(Task[_T]):
        __slots__ = ()

        def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn:
            bcs = _ThreadingTask
            bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

            msg = f"type '{bcs_repr}' is not an acceptable base type"
            raise TypeError(msg)

        def __reduce__(self, /) -> NoReturn:
            msg = f"cannot reduce {self!r}"
            raise TypeError(msg)

        def _run(self, /) -> _T:
            try:
                self._started.future.set_result(True)

                if isawaitable(self._func) or iscoroutinefunction(self._func):
                    msg = f"a green function was expected, got {self._func!r}"
                    raise TypeError(msg)

                result = self._func(*self._args)
            except _CancelledError as exc:
                exc_cls = exc.__class__
                exc_cls_repr = f"{exc_cls.__module__}.{exc_cls.__qualname__}"

                msg = f"task raised {exc_cls_repr}"
                raise RuntimeError(msg) from exc
            finally:
                self = None  # noqa: PLW0642

            return result

        def _cancel(self, /) -> bool:
            self._started.wait()

            return False

    return _ThreadingTask


@once
def _get_eventlet_task_class() -> type[Task[_T]]:
    import eventlet

    @final
    class _EventletTask(Task[_T]):
        __slots__ = ("_greenlet",)

        def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn:
            bcs = _EventletTask
            bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

            msg = f"type '{bcs_repr}' is not an acceptable base type"
            raise TypeError(msg)

        def __reduce__(self, /) -> NoReturn:
            msg = f"cannot reduce {self!r}"
            raise TypeError(msg)

        def _run(self, /) -> _T:
            self._greenlet = eventlet.getcurrent()

            try:
                self._started.future.set_result(True)

                if isawaitable(self._func) or iscoroutinefunction(self._func):
                    msg = f"a green function was expected, got {self._func!r}"
                    raise TypeError(msg)

                result = self._func(*self._args)
            except get_cancelled_exc_class() as exc:
                self._cancelled_after_start = True

                raise _CancelledError from exc
            except _CancelledError as exc:
                exc_cls = exc.__class__
                exc_cls_repr = f"{exc_cls.__module__}.{exc_cls.__qualname__}"

                msg = f"task raised {exc_cls_repr}"
                raise RuntimeError(msg) from exc
            finally:
                del self._greenlet
                self = None  # noqa: PLW0642

            return result

        def _cancel(self, /) -> bool:
            self._started.wait()

            if (greenlet := getattr(self, "_greenlet", None)) is not None:
                greenlet.kill()

                return True

            return self._cancelled_after_start

    return _EventletTask


@once
def _get_gevent_task_class() -> type[Task[_T]]:
    import gevent

    @final
    class _GeventTask(Task[_T]):
        __slots__ = ("_greenlet",)

        def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn:
            bcs = _GeventTask
            bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

            msg = f"type '{bcs_repr}' is not an acceptable base type"
            raise TypeError(msg)

        def __reduce__(self, /) -> NoReturn:
            msg = f"cannot reduce {self!r}"
            raise TypeError(msg)

        def _run(self, /) -> _T:
            self._greenlet = gevent.getcurrent()

            try:
                self._started.future.set_result(True)

                if isawaitable(self._func) or iscoroutinefunction(self._func):
                    msg = f"a green function was expected, got {self._func!r}"
                    raise TypeError(msg)

                result = self._func(*self._args)
            except get_cancelled_exc_class() as exc:
                self._cancelled_after_start = True

                raise _CancelledError from exc
            except _CancelledError as exc:
                exc_cls = exc.__class__
                exc_cls_repr = f"{exc_cls.__module__}.{exc_cls.__qualname__}"

                msg = f"task raised {exc_cls_repr}"
                raise RuntimeError(msg) from exc
            finally:
                del self._greenlet
                self = None  # noqa: PLW0642

            return result

        def _cancel(self, /) -> bool:
            self._started.wait()

            if (greenlet := getattr(self, "_greenlet", None)) is not None:
                greenlet.kill(block=False)

                return True

            return self._cancelled_after_start

    return _GeventTask


@once
def _get_asyncio_task_class() -> type[Task[_T]]:
    import asyncio

    @final
    class _AsyncioTask(Task[_T]):
        __slots__ = ("_task",)

        def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn:
            bcs = _AsyncioTask
            bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

            msg = f"type '{bcs_repr}' is not an acceptable base type"
            raise TypeError(msg)

        def __reduce__(self, /) -> NoReturn:
            msg = f"cannot reduce {self!r}"
            raise TypeError(msg)

        async def _run(self, /) -> _T:
            self._task = asyncio.current_task()

            try:
                self._started.future.set_result(True)

                if isawaitable(self._func):
                    result = await self._func
                else:
                    result = self._func(*self._args)

                    if iscoroutinefunction(self._func):
                        result = await result
            except get_cancelled_exc_class() as exc:
                self._cancelled_after_start = True

                raise _CancelledError from exc
            except _CancelledError as exc:
                exc_cls = exc.__class__
                exc_cls_repr = f"{exc_cls.__module__}.{exc_cls.__qualname__}"

                msg = f"task raised {exc_cls_repr}"
                raise RuntimeError(msg) from exc
            finally:
                del self._task
                self = None  # noqa: PLW0642

            return result

        async def _cancel(self, /) -> bool:
            await self._started

            if (task := getattr(self, "_task", None)) is not None:
                task.cancel()

                return True

            return self._cancelled_after_start

    return _AsyncioTask


@once
def _get_curio_task_class() -> type[Task[_T]]:
    import curio

    @final
    class _CurioTask(Task[_T]):
        __slots__ = ("_task",)

        def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn:
            bcs = _CurioTask
            bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

            msg = f"type '{bcs_repr}' is not an acceptable base type"
            raise TypeError(msg)

        def __reduce__(self, /) -> NoReturn:
            msg = f"cannot reduce {self!r}"
            raise TypeError(msg)

        async def _run(self, /) -> _T:
            self._task = await curio.current_task()

            try:
                self._started.future.set_result(True)

                if isawaitable(self._func):
                    result = await self._func
                else:
                    result = self._func(*self._args)

                    if iscoroutinefunction(self._func):
                        result = await result
            except get_cancelled_exc_class() as exc:
                self._cancelled_after_start = True

                raise _CancelledError from exc
            except _CancelledError as exc:
                exc_cls = exc.__class__
                exc_cls_repr = f"{exc_cls.__module__}.{exc_cls.__qualname__}"

                msg = f"task raised {exc_cls_repr}"
                raise RuntimeError(msg) from exc
            finally:
                del self._task
                self = None  # noqa: PLW0642

            return result

        async def _cancel(self, /) -> bool:
            await self._started

            if (task := getattr(self, "_task", None)) is not None:
                await task.cancel(blocking=False)

                return True

            return self._cancelled_after_start

    return _CurioTask


@once
def _get_trio_task_class() -> type[Task[_T]]:
    import trio

    @final
    class _TrioTask(Task[_T]):
        __slots__ = ("_cancel_scope",)

        def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn:
            bcs = _TrioTask
            bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

            msg = f"type '{bcs_repr}' is not an acceptable base type"
            raise TypeError(msg)

        def __reduce__(self, /) -> NoReturn:
            msg = f"cannot reduce {self!r}"
            raise TypeError(msg)

        async def _run(self, /) -> _T:
            self._cancel_scope = trio.CancelScope().__enter__()

            try:
                self._started.future.set_result(True)

                if isawaitable(self._func):
                    result = await self._func
                else:
                    result = self._func(*self._args)

                    if iscoroutinefunction(self._func):
                        result = await result
            except get_cancelled_exc_class() as exc:
                self._cancelled_after_start = True

                raise _CancelledError from exc
            except _CancelledError as exc:
                exc_cls = exc.__class__
                exc_cls_repr = f"{exc_cls.__module__}.{exc_cls.__qualname__}"

                msg = f"task raised {exc_cls_repr}"
                raise RuntimeError(msg) from exc
            finally:
                self._cancel_scope.__exit__(*sys.exc_info())
                del self._cancel_scope
                self = None  # noqa: PLW0642

            return result

        async def _cancel(self, /) -> bool:
            await self._started

            if (scope := getattr(self, "_cancel_scope", None)) is not None:
                scope.cancel()

                return True

            return self._cancelled_after_start

    return _TrioTask


@once
def _get_anyio_task_class() -> type[Task[_T]]:
    import anyio

    @final
    class _AnyioTask(Task[_T]):
        __slots__ = ("_cancel_scope",)

        def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn:
            bcs = _AnyioTask
            bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

            msg = f"type '{bcs_repr}' is not an acceptable base type"
            raise TypeError(msg)

        def __reduce__(self, /) -> NoReturn:
            msg = f"cannot reduce {self!r}"
            raise TypeError(msg)

        async def _run(self, /) -> _T:
            self._cancel_scope = anyio.CancelScope().__enter__()

            try:
                self._started.future.set_result(True)

                if isawaitable(self._func):
                    result = await self._func
                else:
                    result = self._func(*self._args)

                    if iscoroutinefunction(self._func):
                        result = await result
            except get_cancelled_exc_class() as exc:
                self._cancelled_after_start = True

                raise _CancelledError from exc
            except _CancelledError as exc:
                exc_cls = exc.__class__
                exc_cls_repr = f"{exc_cls.__module__}.{exc_cls.__qualname__}"

                msg = f"task raised {exc_cls_repr}"
                raise RuntimeError(msg) from exc
            finally:
                self._cancel_scope.__exit__(*sys.exc_info())
                del self._cancel_scope
                self = None  # noqa: PLW0642

            return result

        async def _cancel(self, /) -> bool:
            await self._started

            if (scope := getattr(self, "_cancel_scope", None)) is not None:
                scope.cancel()

                return True

            return self._cancelled_after_start

    return _AnyioTask


@overload
def _create_threading_task(
    func: Awaitable[_T],
    /,
    *,
    executor: TaskExecutor,
) -> Task[_T]: ...
@overload
def _create_threading_task(
    func: Callable[[Unpack[_Ts]], Coroutine[Any, Any, _T]],
    /,
    *args: Unpack[_Ts],
    executor: TaskExecutor,
) -> Task[_T]: ...
@overload
def _create_threading_task(
    func: Callable[[Unpack[_Ts]], _T],
    /,
    *args: Unpack[_Ts],
    executor: TaskExecutor,
) -> Task[_T]: ...
def _create_threading_task(func, /, *args, executor):
    global _create_threading_task

    _create_threading_task = _get_threading_task_class()

    return _create_threading_task(func, *args, executor=executor)


@overload
def _create_eventlet_task(
    func: Awaitable[_T],
    /,
    *,
    executor: TaskExecutor,
) -> Task[_T]: ...
@overload
def _create_eventlet_task(
    func: Callable[[Unpack[_Ts]], Coroutine[Any, Any, _T]],
    /,
    *args: Unpack[_Ts],
    executor: TaskExecutor,
) -> Task[_T]: ...
@overload
def _create_eventlet_task(
    func: Callable[[Unpack[_Ts]], _T],
    /,
    *args: Unpack[_Ts],
    executor: TaskExecutor,
) -> Task[_T]: ...
def _create_eventlet_task(func, /, *args, executor):
    global _create_eventlet_task

    _create_eventlet_task = _get_eventlet_task_class()

    return _create_eventlet_task(func, *args, executor=executor)


@overload
def _create_gevent_task(
    func: Awaitable[_T],
    /,
    *,
    executor: TaskExecutor,
) -> Task[_T]: ...
@overload
def _create_gevent_task(
    func: Callable[[Unpack[_Ts]], Coroutine[Any, Any, _T]],
    /,
    *args: Unpack[_Ts],
    executor: TaskExecutor,
) -> Task[_T]: ...
@overload
def _create_gevent_task(
    func: Callable[[Unpack[_Ts]], _T],
    /,
    *args: Unpack[_Ts],
    executor: TaskExecutor,
) -> Task[_T]: ...
def _create_gevent_task(func, /, *args, executor):
    global _create_gevent_task

    _create_gevent_task = _get_gevent_task_class()

    return _create_gevent_task(func, *args, executor=executor)


@overload
def _create_asyncio_task(
    func: Awaitable[_T],
    /,
    *,
    executor: TaskExecutor,
) -> Task[_T]: ...
@overload
def _create_asyncio_task(
    func: Callable[[Unpack[_Ts]], Coroutine[Any, Any, _T]],
    /,
    *args: Unpack[_Ts],
    executor: TaskExecutor,
) -> Task[_T]: ...
@overload
def _create_asyncio_task(
    func: Callable[[Unpack[_Ts]], _T],
    /,
    *args: Unpack[_Ts],
    executor: TaskExecutor,
) -> Task[_T]: ...
def _create_asyncio_task(func, /, *args, executor):
    global _create_asyncio_task

    _create_asyncio_task = _get_asyncio_task_class()

    return _create_asyncio_task(func, *args, executor=executor)


@overload
def _create_curio_task(
    func: Awaitable[_T],
    /,
    *,
    executor: TaskExecutor,
) -> Task[_T]: ...
@overload
def _create_curio_task(
    func: Callable[[Unpack[_Ts]], Coroutine[Any, Any, _T]],
    /,
    *args: Unpack[_Ts],
    executor: TaskExecutor,
) -> Task[_T]: ...
@overload
def _create_curio_task(
    func: Callable[[Unpack[_Ts]], _T],
    /,
    *args: Unpack[_Ts],
    executor: TaskExecutor,
) -> Task[_T]: ...
def _create_curio_task(func, /, *args, executor):
    global _create_curio_task

    _create_curio_task = _get_curio_task_class()

    return _create_curio_task(func, *args, executor=executor)


@overload
def _create_trio_task(
    func: Awaitable[_T],
    /,
    *,
    executor: TaskExecutor,
) -> Task[_T]: ...
@overload
def _create_trio_task(
    func: Callable[[Unpack[_Ts]], Coroutine[Any, Any, _T]],
    /,
    *args: Unpack[_Ts],
    executor: TaskExecutor,
) -> Task[_T]: ...
@overload
def _create_trio_task(
    func: Callable[[Unpack[_Ts]], _T],
    /,
    *args: Unpack[_Ts],
    executor: TaskExecutor,
) -> Task[_T]: ...
def _create_trio_task(func, /, *args, executor):
    global _create_trio_task

    _create_trio_task = _get_trio_task_class()

    return _create_trio_task(func, *args, executor=executor)


@overload
def _create_anyio_task(
    func: Awaitable[_T],
    /,
    *,
    executor: TaskExecutor,
) -> Task[_T]: ...
@overload
def _create_anyio_task(
    func: Callable[[Unpack[_Ts]], Coroutine[Any, Any, _T]],
    /,
    *args: Unpack[_Ts],
    executor: TaskExecutor,
) -> Task[_T]: ...
@overload
def _create_anyio_task(
    func: Callable[[Unpack[_Ts]], _T],
    /,
    *args: Unpack[_Ts],
    executor: TaskExecutor,
) -> Task[_T]: ...
def _create_anyio_task(func, /, *args, executor):
    global _create_anyio_task

    _create_anyio_task = _get_anyio_task_class()

    return _create_anyio_task(func, *args, executor=executor)


@overload
def create_task(
    func: Awaitable[_T],
    /,
    *,
    executor: TaskExecutor | DefaultType = DEFAULT,
) -> Task[_T]: ...
@overload
def create_task(
    func: Callable[[Unpack[_Ts]], Coroutine[Any, Any, _T]],
    /,
    *args: Unpack[_Ts],
    executor: TaskExecutor | DefaultType = DEFAULT,
) -> Task[_T]: ...
@overload
def create_task(
    func: Callable[[Unpack[_Ts]], _T],
    /,
    *args: Unpack[_Ts],
    executor: TaskExecutor | DefaultType = DEFAULT,
) -> Task[_T]: ...
def create_task(func, /, *args, executor=DEFAULT):
    if executor is DEFAULT:
        executor = current_executor()

    library = executor.library

    if library == "threading":
        impl = _create_threading_task
    elif library == "eventlet":
        impl = _create_eventlet_task
    elif library == "gevent":
        impl = _create_gevent_task
    elif library == "asyncio":
        impl = _create_asyncio_task
    elif library == "curio":
        impl = _create_curio_task
    elif library == "trio":
        impl = _create_trio_task
    elif library == "anyio":
        impl = _create_anyio_task
    else:
        msg = f"unsupported library {library!r}"
        raise RuntimeError(msg)

    return impl(func, *args, executor=executor)
