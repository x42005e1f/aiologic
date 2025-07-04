#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from abc import ABC, abstractmethod
from concurrent.futures import Future
from typing import Any, Generic, TypeVar, overload

from ._executors import TaskExecutor

if sys.version_info >= (3, 11):
    from typing import TypeVarTuple, Unpack
else:
    from typing_extensions import TypeVarTuple, Unpack

if sys.version_info >= (3, 9):
    from collections.abc import Callable, Coroutine, Generator
else:
    from typing import Callable, Coroutine, Generator

_T = TypeVar("_T")
_Ts = TypeVarTuple("_Ts")

def _get_threading_cancelled_exc_class() -> type[BaseException]: ...
def _get_eventlet_cancelled_exc_class() -> type[BaseException]: ...
def _get_gevent_cancelled_exc_class() -> type[BaseException]: ...
def _get_asyncio_cancelled_exc_class() -> type[BaseException]: ...
def _get_curio_cancelled_exc_class() -> type[BaseException]: ...
def _get_trio_cancelled_exc_class() -> type[BaseException]: ...
def get_cancelled_exc_class(
    *,
    executor: TaskExecutor | None = None,
    failback: type[BaseException] | None = None,
) -> type[BaseException]: ...
def _get_threading_timeout_exc_class() -> type[BaseException]: ...
def _get_eventlet_timeout_exc_class() -> type[BaseException]: ...
def _get_gevent_timeout_exc_class() -> type[BaseException]: ...
def _get_asyncio_timeout_exc_class() -> type[BaseException]: ...
def _get_curio_timeout_exc_class() -> type[BaseException]: ...
def _get_trio_timeout_exc_class() -> type[BaseException]: ...
def get_timeout_exc_class(
    *,
    executor: TaskExecutor | None = None,
    failback: type[BaseException] | None = None,
) -> type[BaseException]: ...

_CancelledError: type[BaseException]
_TimeoutError: type[BaseException]

class Result(Generic[_T]):
    __slots__ = ("_future",)

    def __init__(self, /, future: Future[_T]) -> None: ...
    def __repr__(self, /) -> str: ...
    def __bool__(self, /) -> bool: ...
    def __await__(self) -> Generator[Any, Any, _T]: ...
    def wait(self, timeout: float | None = None) -> _T: ...
    @property
    def future(self, /) -> Future[_T]: ...

class Task(Result[_T], ABC):
    __slots__ = (
        "_args",
        "_cancelled",
        "_executor",
        "_func",
        "_started",
    )

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
    def __repr__(self, /) -> str: ...
    def __await__(self) -> Generator[Any, Any, _T]: ...
    def wait(self, timeout: float | None = None) -> _T: ...
    def cancel(self, /) -> Result[bool]: ...
    def cancelled(self, /) -> Result[bool]: ...
    def running(self, /) -> Result[bool]: ...
    def done(self, /) -> Result[bool]: ...
    @abstractmethod
    def _run(self, /) -> Coroutine[Any, Any, _T] | _T: ...
    @abstractmethod
    def _cancel(self, /) -> Coroutine[Any, Any, bool] | bool: ...
    @property
    def executor(self, /) -> TaskExecutor: ...

def _get_threading_task_class() -> type[Task[_T]]: ...
def _get_eventlet_task_class() -> type[Task[_T]]: ...
def _get_gevent_task_class() -> type[Task[_T]]: ...
def _get_asyncio_task_class() -> type[Task[_T]]: ...
def _get_curio_task_class() -> type[Task[_T]]: ...
def _get_trio_task_class() -> type[Task[_T]]: ...
def _get_anyio_task_class() -> type[Task[_T]]: ...
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
@overload
def create_task(
    func: Callable[[Unpack[_Ts]], Coroutine[Any, Any, _T]],
    /,
    *args: Unpack[_Ts],
    executor: TaskExecutor | None = None,
) -> Task[_T]: ...
@overload
def create_task(
    func: Callable[[Unpack[_Ts]], _T],
    /,
    *args: Unpack[_Ts],
    executor: TaskExecutor | None = None,
) -> Task[_T]: ...
