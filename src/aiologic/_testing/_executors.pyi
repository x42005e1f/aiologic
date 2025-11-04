#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys
import threading

from abc import ABC, abstractmethod
from concurrent.futures import Executor, Future
from contextvars import Context
from types import TracebackType
from typing import Any, Generic, NoReturn, TypeVar, final

from aiologic.meta import DEFAULT, DefaultType

if sys.version_info >= (3, 11):
    from typing import Self, overload
else:
    from typing_extensions import Self, overload

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

if sys.version_info >= (3, 9):
    from collections.abc import Awaitable, Callable, Coroutine
else:
    from typing import Awaitable, Callable, Coroutine

_T = TypeVar("_T")
_P = ParamSpec("_P")

class _ExecutorLocal(threading.local):
    executor: TaskExecutor | None = None

_executor_tlocal: _ExecutorLocal

@final
class _WorkItem(Generic[_T]):
    __slots__ = (
        "_args",
        "_context",
        "_func",
        "_future",
        "_kwargs",
        "_new_task",
    )

    @overload
    def __init__(self, future: Future[_T], func: Awaitable[_T], /): ...
    @overload
    def __init__(
        self,
        future: Future[_T],
        func: Callable[_P, Coroutine[Any, Any, _T]],
        /,
        *args: _P.args,
        **kwargs: _P.kwargs,
    ) -> None: ...
    @overload
    def __init__(
        self,
        future: Future[_T],
        func: Callable[_P, _T],
        /,
        *args: _P.args,
        **kwargs: _P.kwargs,
    ) -> None: ...
    def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn: ...
    def __reduce__(self, /) -> NoReturn: ...
    async def async_run(self, /) -> None: ...
    def green_run(self, /, executor: TaskExecutor | None = None) -> None: ...
    def add_done_callback(self, func: Callable[[], object], /) -> None: ...
    def cancel(self, /) -> None: ...
    def abort(self, /, cause: BaseException) -> None: ...
    @property
    def future(self, /) -> Future[_T]: ...
    @property
    def context(self, /) -> Context: ...
    @context.setter
    def context(self, /, value: Context) -> None: ...
    @property
    def new_task(self, /) -> bool: ...
    @new_task.setter
    def new_task(self, /, value: bool) -> None: ...

class TaskExecutor(Executor, ABC):
    __slots__ = (
        "_backend",
        "_backend_options",
        "_broken_by",
        "_library",
        "_shutdown",
        "_shutdown_event",
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
    ) -> None: ...
    def __repr__(self, /) -> str: ...
    async def __aenter__(self, /) -> Self: ...
    def __enter__(self, /) -> Self: ...
    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...
    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...
    @overload
    def _create_work_item(self, fn: Awaitable[_T], /) -> _WorkItem[_T]: ...
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
    def _create_task(self, /, work_item: _WorkItem[Any]) -> None: ...
    @overload
    def schedule(self, fn: Awaitable[_T], /) -> Future[_T]: ...
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
    if sys.version_info >= (3, 9):
        @overload
        def submit(self, fn: Awaitable[_T], /) -> Future[_T]: ...
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

    else:
        @overload
        def submit(self, fn: Awaitable[_T]) -> Future[_T]: ...
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
    @overload
    def _submit_with_context(
        self,
        fn: Awaitable[_T],
        /,
        context: Context,
    ) -> Future[_T]: ...
    @overload
    def _submit_with_context(
        self,
        fn: Callable[[], Coroutine[Any, Any, _T]],
        /,
        context: Context,
    ) -> Future[_T]: ...
    @overload
    def _submit_with_context(
        self,
        fn: Callable[[], _T],
        /,
        context: Context,
    ) -> Future[_T]: ...
    def shutdown(
        self,
        wait: bool = True,
        *,
        cancel_futures: bool = False,
    ) -> None: ...
    def _abort(self, /, cause: BaseException) -> None: ...
    @abstractmethod
    def _run(self, /) -> None: ...
    @property
    def backend(self, /) -> str: ...
    @property
    def library(self, /) -> str: ...

def _get_threading_executor_class() -> type[TaskExecutor]: ...
def _get_eventlet_executor_class() -> type[TaskExecutor]: ...
def _get_gevent_executor_class() -> type[TaskExecutor]: ...
def _get_asyncio_executor_class() -> type[TaskExecutor]: ...
def _get_curio_executor_class() -> type[TaskExecutor]: ...
def _get_trio_executor_class() -> type[TaskExecutor]: ...
def _get_anyio_executor_class() -> type[TaskExecutor]: ...
def _create_threading_executor(
    library: str,
    backend: str,
    backend_options: dict[str, Any],
) -> TaskExecutor: ...
def _create_eventlet_executor(
    library: str,
    backend: str,
    backend_options: dict[str, Any],
) -> TaskExecutor: ...
def _create_gevent_executor(
    library: str,
    backend: str,
    backend_options: dict[str, Any],
) -> TaskExecutor: ...
def _create_asyncio_executor(
    library: str,
    backend: str,
    backend_options: dict[str, Any],
) -> TaskExecutor: ...
def _create_curio_executor(
    library: str,
    backend: str,
    backend_options: dict[str, Any],
) -> TaskExecutor: ...
def _create_trio_executor(
    library: str,
    backend: str,
    backend_options: dict[str, Any],
) -> TaskExecutor: ...
def _create_anyio_executor(
    library: str,
    backend: str,
    backend_options: dict[str, Any],
) -> TaskExecutor: ...
@overload
def create_executor(
    library: str,
    backend: str | DefaultType = DEFAULT,
    backend_options: dict[str, Any] | None = None,
) -> TaskExecutor: ...
@overload
def create_executor(
    library: DefaultType = DEFAULT,
    *,
    backend: str,
    backend_options: dict[str, Any] | None = None,
) -> TaskExecutor: ...
def current_executor(*, failsafe: bool = False) -> TaskExecutor: ...
