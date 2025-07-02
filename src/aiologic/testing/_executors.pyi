#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys
import threading

from concurrent.futures import Executor, Future
from typing import Any, TypeVar, overload

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

if sys.version_info >= (3, 9):
    from collections.abc import Awaitable, Callable
else:
    from typing import Awaitable, Callable

_T = TypeVar("_T")
_P = ParamSpec("_P")

class _ExecutorLocal(threading.local):
    executor: _TaskExecutor | None = None

_executor_tlocal: _ExecutorLocal

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
    ) -> None: ...
    async def async_run(self, /) -> None: ...
    def green_run(self, /, executor: _TaskExecutor | None = None) -> None: ...
    def add_done_callback(self, func: Callable[[], object], /) -> None: ...
    def cancel(self, /) -> None: ...
    def abort(self, /, cause: BaseException) -> None: ...

class _TaskExecutor(Executor):
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
    ) -> None: ...
    if sys.version_info >= (3, 9):
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

    else:
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
    def shutdown(
        self,
        wait: bool = True,
        *,
        cancel_futures: bool = False,
    ) -> None: ...
    def _abort(self, /, cause: BaseException) -> None: ...
    def _run(self, /) -> None: ...
    @property
    def backend(self, /) -> str: ...
    @property
    def library(self, /) -> str: ...

def _get_threading_executor_class() -> type[_TaskExecutor]: ...
def _get_eventlet_executor_class() -> type[_TaskExecutor]: ...
def _get_gevent_executor_class() -> type[_TaskExecutor]: ...
def _get_asyncio_executor_class() -> type[_TaskExecutor]: ...
def _get_curio_executor_class() -> type[_TaskExecutor]: ...
def _get_trio_executor_class() -> type[_TaskExecutor]: ...
def _get_anyio_executor_class() -> type[_TaskExecutor]: ...
def _create_threading_executor(
    library: str,
    backend: str,
    backend_options: dict[str, Any],
) -> _TaskExecutor: ...
def _create_eventlet_executor(
    library: str,
    backend: str,
    backend_options: dict[str, Any],
) -> _TaskExecutor: ...
def _create_gevent_executor(
    library: str,
    backend: str,
    backend_options: dict[str, Any],
) -> _TaskExecutor: ...
def _create_asyncio_executor(
    library: str,
    backend: str,
    backend_options: dict[str, Any],
) -> _TaskExecutor: ...
def _create_curio_executor(
    library: str,
    backend: str,
    backend_options: dict[str, Any],
) -> _TaskExecutor: ...
def _create_trio_executor(
    library: str,
    backend: str,
    backend_options: dict[str, Any],
) -> _TaskExecutor: ...
def _create_anyio_executor(
    library: str,
    backend: str,
    backend_options: dict[str, Any],
) -> _TaskExecutor: ...
def create_executor(
    library: str,
    backend: str | None = None,
    backend_options: dict[str, Any] | None = None,
) -> _TaskExecutor: ...
def current_executor() -> _TaskExecutor: ...
