#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys
import threading

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, NoReturn, TypeVar, final

from aiologic.lowlevel import (
    DUMMY_EVENT,
    create_async_event,
    create_green_event,
)
from aiologic.meta import DEFAULT, DefaultType

from ._executors import TaskExecutor, current_executor
from ._tasks import Task, TaskCancelled, create_task as _create_task

if sys.version_info >= (3, 11):
    from typing import Self, TypeVarTuple, Unpack, overload
else:
    from exceptiongroup import BaseExceptionGroup
    from typing_extensions import Self, TypeVarTuple, Unpack, overload

if TYPE_CHECKING:
    from concurrent.futures import Future
    from types import TracebackType

    if sys.version_info >= (3, 9):
        from collections.abc import Awaitable, Callable, Coroutine
    else:
        from typing import Awaitable, Callable, Coroutine

_TaskT = TypeVar("_TaskT", bound=Task[Any])
_T = TypeVar("_T")
_Ts = TypeVarTuple("_Ts")


class TaskGroup(ABC):
    __slots__ = (
        "_active",
        "_active_lock",
        "_cancelling",
        "_event",
        "_executor",
        "_remaining",
        "_tasks",
    )

    def __init__(self, /, *, executor: TaskExecutor) -> None:
        self._active = False
        self._active_lock = threading.RLock()
        self._executor = executor

    def __repr__(self, /) -> str:
        cls = self.__class__
        if cls.__module__ == __name__:
            cls = TaskGroup
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        executor = self._executor

        if executor.library != executor.backend:
            executor_repr = f"<{executor.library}+{executor.backend}>"
        else:
            executor_repr = f"<{executor.library}>"

        object_repr = f"{cls_repr}(executor={executor_repr})"

        if not self._active:
            extra = "inactive"
        elif self._cancelling:
            extra = f"cancelling, tasks={self._remaining}"
        else:
            extra = f"active, tasks={self._remaining}"

        return f"<{object_repr} at {id(self):#x} [{extra}]>"

    async def __aenter__(self, /) -> Self:
        with self._active_lock:
            if self._active:
                msg = "this task group is already active"
                raise RuntimeError(msg)

            self._active = True
            self._cancelling = False
            self._remaining = 0

            self._event = DUMMY_EVENT
            self._tasks = []

        return self

    def __enter__(self, /) -> Self:
        with self._active_lock:
            if self._active:
                msg = "this task group is already active"
                raise RuntimeError(msg)

            self._active = True
            self._cancelling = False
            self._remaining = 0

            self._event = DUMMY_EVENT
            self._tasks = []

        return self

    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        suppress = (
            exc_value is not None
            and isinstance(exc_value, TaskCancelled)
            and exc_value.task in self._tasks
        )

        active_lock = self._active_lock
        active_lock.acquire()
        active_lock_acquired = True

        try:
            try:
                if exc_value is None:
                    while self._remaining:
                        self._event = create_async_event()

                        active_lock_acquired = False
                        active_lock.release()

                        await self._event

                        active_lock.acquire()
                        active_lock_acquired = True
            finally:
                if not active_lock_acquired:
                    active_lock.acquire()

                self._cancelling = True

                for task in self._tasks:
                    task.cancel()

                while self._remaining:
                    self._event = create_async_event(shield=True)

                    active_lock_acquired = False
                    active_lock.release()

                    await self._event

                    active_lock.acquire()
                    active_lock_acquired = True

                self._active = False

                exceptions = []

                for task in self._tasks:
                    if task.cancelled():
                        continue

                    exception = task.future.exception()

                    if exception is exc_value:
                        continue

                    if exception is not None:
                        exceptions.append(exception)

                del self._tasks

                if exceptions:
                    msg = "unhandled errors in a task group"
                    raise BaseExceptionGroup(msg, exceptions)
        finally:
            if active_lock_acquired:
                active_lock.release()

        return suppress

    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        suppress = (
            exc_value is not None
            and isinstance(exc_value, TaskCancelled)
            and exc_value.task in self._tasks
        )

        active_lock = self._active_lock
        active_lock.acquire()
        active_lock_acquired = True

        try:
            try:
                if exc_value is None:
                    while self._remaining:
                        self._event = create_green_event()

                        active_lock_acquired = False
                        active_lock.release()

                        self._event.wait()

                        active_lock.acquire()
                        active_lock_acquired = True
            finally:
                if not active_lock_acquired:
                    active_lock.acquire()

                self._cancelling = True

                for task in self._tasks:
                    task.cancel()

                while self._remaining:
                    self._event = create_green_event(shield=True)

                    active_lock_acquired = False
                    active_lock.release()

                    self._event.wait()

                    active_lock.acquire()
                    active_lock_acquired = True

                self._active = False

                exceptions = []

                for task in self._tasks:
                    if task.cancelled():
                        continue

                    exception = task.future.exception()

                    if exception is exc_value:
                        continue

                    if exception is not None:
                        exceptions.append(exception)

                del self._tasks

                if exceptions:
                    msg = "unhandled errors in a task group"
                    raise BaseExceptionGroup(msg, exceptions)
        finally:
            if active_lock_acquired:
                active_lock.release()

        return suppress

    @overload
    def create_task(
        self,
        func: Awaitable[_T],
        /,
        *,
        executor: TaskExecutor | DefaultType = DEFAULT,
    ) -> Task[_T]: ...
    @overload
    def create_task(
        self,
        func: Callable[[Unpack[_Ts]], Coroutine[Any, Any, _T]],
        /,
        *args: Unpack[_Ts],
        executor: TaskExecutor | DefaultType = DEFAULT,
    ) -> Task[_T]: ...
    @overload
    def create_task(
        self,
        func: Callable[[Unpack[_Ts]], _T],
        /,
        *args: Unpack[_Ts],
        executor: TaskExecutor | DefaultType = DEFAULT,
    ) -> Task[_T]: ...
    def create_task(self, func, /, *args, executor=DEFAULT):
        with self._active_lock:
            if not self._active:
                msg = "this task group is not active"
                raise RuntimeError(msg)

            if executor is DEFAULT:
                executor = self._executor

            return self.add_task(_create_task(func, *args, executor=executor))

    def add_task(self, /, task: _TaskT) -> _TaskT:
        with self._active_lock:
            if not self._active:
                msg = "this task group is not active"
                raise RuntimeError(msg)

            self._tasks.append(task)
            task.future.add_done_callback(self._callback)

            if self._cancelling:
                task.cancel()

            self._remaining += 1

            return task

    @abstractmethod
    def _callback(self, /, future: Future[object]) -> None:
        raise NotImplementedError

    @property
    def executor(self, /) -> TaskExecutor:
        return self._executor


@final
class _WaitAllTaskGroup(TaskGroup):
    __slots__ = ()

    def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn:
        bcs = _WaitAllTaskGroup
        bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

        msg = f"type '{bcs_repr}' is not an acceptable base type"
        raise TypeError(msg)

    def __reduce__(self, /) -> NoReturn:
        msg = f"cannot reduce {self!r}"
        raise TypeError(msg)

    def _callback(self, /, future: Future[object]) -> None:
        with self._active_lock:
            self._remaining -= 1

            if not self._remaining or (
                not self._cancelling
                and (future.cancelled() or future.exception() is not None)
            ):
                self._event.set()


def create_task_group(
    *,
    executor: TaskExecutor | DefaultType = DEFAULT,
) -> TaskGroup:
    if executor is DEFAULT:
        executor = current_executor()

    return _WaitAllTaskGroup(executor=executor)
