#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from abc import ABC, abstractmethod
from concurrent.futures import Future
from types import TracebackType
from typing import Any, NoReturn, TypeVar, final

from aiologic.meta import DEFAULT, DefaultType

from ._executors import TaskExecutor
from ._tasks import Task

if sys.version_info >= (3, 11):
    from typing import Self, TypeVarTuple, Unpack, overload
else:
    from typing_extensions import Self, TypeVarTuple, Unpack, overload

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

    def __init__(self, /, *, executor: TaskExecutor) -> None: ...
    def __repr__(self, /) -> str: ...
    async def __aenter__(self, /) -> Self: ...
    def __enter__(self, /) -> Self: ...
    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool: ...
    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool: ...
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
    def add_task(self, /, task: _TaskT) -> _TaskT: ...
    @abstractmethod
    def _callback(self, /, future: Future[object]) -> None: ...
    @property
    def executor(self, /) -> TaskExecutor: ...

@final
class _WaitAllTaskGroup(TaskGroup):
    __slots__ = ()

    def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn: ...
    def __reduce__(self, /) -> NoReturn: ...
    def _callback(self, /, future: Future[object]) -> None: ...

def create_task_group(
    *,
    executor: TaskExecutor | DefaultType = DEFAULT,
) -> TaskGroup: ...
