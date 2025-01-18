#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import _thread
import sys
import threading

from types import TracebackType
from typing import Any, Callable, Generator, Generic, TypeVar, overload

from ._lock import Lock, PLock, RLock

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

_T_co = TypeVar(
    "_T_co",
    bound=(
        RLock
        | Lock
        | PLock
        | threading.RLock
        | threading.Lock
        | _thread.LockType
        | None
    ),
    covariant=True,
)

class Condition(Generic[_T_co]):
    @overload
    def __new__(cls, /) -> Condition[RLock]: ...
    @overload
    def __new__(cls, /, lock: _T_co) -> Self: ...
    def __bool__(self, /) -> bool: ...
    @overload
    async def __aenter__(self: Condition[None]) -> Condition[None]: ...
    @overload
    async def __aenter__(self: Condition[threading.Lock]) -> bool: ...
    @overload
    async def __aenter__(self: Condition[threading.RLock]) -> bool: ...
    @overload
    async def __aenter__(self: Condition[PLock]) -> PLock: ...
    @overload
    async def __aenter__(self: Condition[Lock]) -> Lock: ...
    @overload
    async def __aenter__(self: Condition[RLock]) -> RLock: ...
    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...
    @overload
    def __enter__(self: Condition[None]) -> Condition[None]: ...
    @overload
    def __enter__(self: Condition[threading.Lock]) -> bool: ...
    @overload
    def __enter__(self: Condition[threading.RLock]) -> bool: ...
    @overload
    def __enter__(self: Condition[PLock]) -> PLock: ...
    @overload
    def __enter__(self: Condition[Lock]) -> Lock: ...
    @overload
    def __enter__(self: Condition[RLock]) -> RLock: ...
    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...
    def __await__(self, /) -> Generator[Any, Any, bool]: ...
    def wait(self, /, timeout: float | None = None) -> bool: ...
    def wait_for(
        self,
        /,
        predicate: Callable[[], bool],
        timeout: float | None = None,
    ) -> bool: ...
    def notify(self, /, count: int = 1) -> int: ...
    def notify_all(self, /) -> int: ...
    @property
    def waiting(self, /) -> int: ...
    @property
    def lock(self, /) -> _T_co: ...
