#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from logging import Logger
from types import TracebackType
from typing import Any, Final, Generic

from . import lowlevel
from ._lock import Lock, RLock
from ._semaphore import BinarySemaphore
from .meta import DEFAULT, DefaultType

if sys.version_info >= (3, 13):
    from typing import TypeVar
else:
    from typing_extensions import TypeVar

if sys.version_info >= (3, 11):
    from typing import Self, overload
else:
    from typing_extensions import Self, overload

if sys.version_info >= (3, 9):
    from collections.abc import Callable, Generator
else:
    from typing import Callable, Generator

_USE_ONCELOCK_FORCED: Final[bool]

LOGGER: Final[Logger]

_T = TypeVar("_T")
_T_co = TypeVar(
    "_T_co",
    bound=(
        Lock
        | BinarySemaphore
        | lowlevel.ThreadRLock
        | lowlevel.ThreadLock
        | None
    ),
    default=RLock,
    covariant=True,
)
_S_co = TypeVar(
    "_S_co",
    bound=Callable[[], float],
    default=Callable[[], float],
    covariant=True,
)

class Condition(Generic[_T_co, _S_co]):
    __slots__ = (
        "__weakref__",
        "_impl",
    )

    @overload
    def __new__(
        cls,
        /,
        lock: DefaultType = DEFAULT,
        timer: DefaultType = DEFAULT,
    ) -> Condition[RLock, Callable[[], int]]: ...
    @overload
    def __new__(
        cls,
        /,
        lock: DefaultType = DEFAULT,
        *,
        timer: _S_co,
    ) -> Condition[RLock, _S_co]: ...
    @overload
    def __new__(
        cls,
        /,
        lock: _T_co,
        timer: DefaultType = DEFAULT,
    ) -> Condition[_T_co, Callable[[], int]]: ...
    @overload
    def __new__(cls, /, lock: _T_co, timer: _S_co) -> Self: ...
    def __getnewargs__(self, /) -> tuple[Any, ...]: ...
    def __getstate__(self, /) -> None: ...
    def __copy__(self, /) -> Self: ...
    def __repr__(self, /) -> str: ...
    def __bool__(self, /) -> bool: ...
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
    def __await__(self, /) -> Generator[Any, Any, bool]: ...
    def wait(self, /, timeout: float | None = None) -> bool: ...
    async def for_(
        self,
        /,
        predicate: Callable[[], _T],
        *,
        delegate: bool = True,
    ) -> _T: ...
    def wait_for(
        self,
        /,
        predicate: Callable[[], _T],
        timeout: float | None = None,
        *,
        delegate: bool = True,
    ) -> _T: ...
    def notify(
        self,
        /,
        count: int = 1,
        *,
        deadline: float | None = None,
    ) -> int: ...
    def notify_all(self, /, *, deadline: float | None = None) -> int: ...
    @property
    def lock(self, /) -> _T_co: ...
    @property
    def timer(self, /) -> _S_co: ...
    @property
    def waiting(self, /) -> int: ...

class _BaseCondition(Condition[_T_co, _S_co]):
    __slots__ = (
        "_lock",
        "_notifying",
        "_timer",
        "_waiters",
    )

    def __new__(cls, /, lock: _T_co, timer: _S_co) -> Self: ...
    def __reduce__(self, /) -> tuple[Any, ...]: ...
    def __copy__(self, /) -> Self: ...
    def __repr__(self, /) -> str: ...
    def __bool__(self, /) -> bool: ...
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
    def __await__(self, /) -> Generator[Any, Any, bool]: ...
    def wait(self, /, timeout: float | None = None) -> bool: ...
    async def for_(
        self,
        /,
        predicate: Callable[[], _T],
        *,
        delegate: bool = True,
    ) -> _T: ...
    def wait_for(
        self,
        /,
        predicate: Callable[[], _T],
        timeout: float | None = None,
        *,
        delegate: bool = True,
    ) -> _T: ...
    def notify(
        self,
        /,
        count: int = 1,
        *,
        deadline: float | None = None,
    ) -> int: ...
    def notify_all(self, /, *, deadline: float | None = None) -> int: ...
    @overload
    async def _async_wait(self, /, predicate: Callable[[], _T]) -> _T: ...
    @overload
    async def _async_wait(self, /, predicate: None) -> bool: ...
    @overload
    def _green_wait(
        self,
        /,
        predicate: Callable[[], _T],
        timeout: float | None,
    ) -> _T: ...
    @overload
    def _green_wait(
        self,
        /,
        predicate: None,
        timeout: float | None,
    ) -> bool: ...
    def _async_owned(self, /) -> bool: ...
    def _green_owned(self, /) -> bool: ...
    @property
    def lock(self, /) -> _T_co: ...
    @property
    def timer(self, /) -> _S_co: ...
    @property
    def waiting(self, /) -> int: ...

class _SyncCondition(_BaseCondition[_T_co, _S_co]):
    __slots__ = ("_counts",)

    def __new__(cls, /, lock: _T_co, timer: _S_co) -> Self: ...
    def __bool__(self, /) -> bool: ...
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
    async def _async_wait(self, /, predicate: Callable[[], _T]) -> _T: ...
    @overload
    async def _async_wait(self, /, predicate: None) -> bool: ...
    @overload
    def _green_wait(
        self,
        /,
        predicate: Callable[[], _T],
        timeout: float | None,
    ) -> _T: ...
    @overload
    def _green_wait(
        self,
        /,
        predicate: None,
        timeout: float | None,
    ) -> bool: ...
    def _async_owned(self, /) -> bool: ...
    def _green_owned(self, /) -> bool: ...

class _RSyncCondition(_BaseCondition[_T_co, _S_co]):
    __slots__ = ()

    def __bool__(self, /) -> bool: ...
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
    async def _async_wait(self, /, predicate: Callable[[], _T]) -> _T: ...
    @overload
    async def _async_wait(self, /, predicate: None) -> bool: ...
    @overload
    def _green_wait(
        self,
        /,
        predicate: Callable[[], _T],
        timeout: float | None,
    ) -> _T: ...
    @overload
    def _green_wait(
        self,
        /,
        predicate: None,
        timeout: float | None,
    ) -> bool: ...
    def _async_owned(self, /) -> bool: ...
    def _green_owned(self, /) -> bool: ...

class _MixedCondition(_BaseCondition[_T_co, _S_co]):
    __slots__ = ("_counts",)

    def __new__(cls, /, lock: _T_co, timer: _S_co) -> Self: ...
    def __bool__(self, /) -> bool: ...
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
    async def for_(
        self,
        /,
        predicate: Callable[[], _T],
        *,
        delegate: bool = True,
    ) -> _T: ...
    def wait_for(
        self,
        /,
        predicate: Callable[[], _T],
        timeout: float | None = None,
        *,
        delegate: bool = True,
    ) -> _T: ...
    def notify(
        self,
        /,
        count: int = 1,
        *,
        deadline: float | None = None,
    ) -> int: ...
    @overload
    async def _async_wait(self, /, predicate: Callable[[], _T]) -> _T: ...
    @overload
    async def _async_wait(self, /, predicate: None) -> bool: ...
    @overload
    def _green_wait(
        self,
        /,
        predicate: Callable[[], _T],
        timeout: float | None,
    ) -> _T: ...
    @overload
    def _green_wait(
        self,
        /,
        predicate: None,
        timeout: float | None,
    ) -> bool: ...
    def _async_owned(self, /) -> bool: ...
    def _green_owned(self, /) -> bool: ...

class _RMixedCondition(_BaseCondition[_T_co, _S_co]):
    __slots__ = ()

    def __bool__(self, /) -> bool: ...
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
    def notify(
        self,
        /,
        count: int = 1,
        *,
        deadline: float | None = None,
    ) -> int: ...
    @overload
    async def _async_wait(self, /, predicate: Callable[[], _T]) -> _T: ...
    @overload
    async def _async_wait(self, /, predicate: None) -> bool: ...
    @overload
    def _green_wait(
        self,
        /,
        predicate: Callable[[], _T],
        timeout: float | None,
    ) -> _T: ...
    @overload
    def _green_wait(
        self,
        /,
        predicate: None,
        timeout: float | None,
    ) -> bool: ...
    def _async_owned(self, /) -> bool: ...
    def _green_owned(self, /) -> bool: ...
