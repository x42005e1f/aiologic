#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from collections import deque
from typing import Any, Generic, Protocol, TypeVar

from .lowlevel import Event
from .meta import MISSING, MissingType

if sys.version_info >= (3, 11):
    from typing import Self, overload
else:
    from typing_extensions import Self, overload

if sys.version_info >= (3, 9):
    from collections.abc import Callable, Iterable
else:
    from typing import Callable, Iterable

_T = TypeVar("_T")
_T_contra = TypeVar("_T_contra", contravariant=True)

class _SupportsBool(Protocol):
    __slots__ = ()

    def __bool__(self, /) -> bool: ...

class _SupportsLT(Protocol[_T_contra]):
    __slots__ = ()

    def __lt__(self, other: _T_contra, /) -> _SupportsBool: ...

class _SupportsGT(Protocol[_T_contra]):
    __slots__ = ()

    def __gt__(self, other: _T_contra, /) -> _SupportsBool: ...

_RichComparableT = TypeVar(
    "_RichComparableT",
    bound=(_SupportsLT[Any] | _SupportsGT[Any]),
)

class QueueEmpty(Exception): ...
class QueueFull(Exception): ...

class SimpleQueue(Generic[_T]):
    __slots__ = (
        "__weakref__",
        "_data",
        "_semaphore",
    )

    def __new__(
        cls,
        items: Iterable[_T] | MissingType = MISSING,
        /,
    ) -> Self: ...
    def __getnewargs__(self, /) -> tuple[Any, ...]: ...
    def __getstate__(self, /) -> None: ...
    def __copy__(self, /) -> Self: ...
    def __repr__(self, /) -> str: ...
    def __bool__(self, /) -> bool: ...
    def __len__(self) -> int: ...
    def copy(self, /) -> Self: ...
    def put(self, /, item: _T) -> None: ...
    async def async_put(
        self,
        /,
        item: _T,
        *,
        blocking: bool = True,
    ) -> None: ...
    def green_put(
        self,
        /,
        item: _T,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> None: ...
    async def async_get(self, /, *, blocking: bool = True) -> _T: ...
    def green_get(
        self,
        /,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> _T: ...
    @property
    def putting(self, /) -> int: ...
    @property
    def getting(self, /) -> int: ...
    @property
    def waiting(self, /) -> int: ...

class SimpleLifoQueue(SimpleQueue[_T]):
    __slots__ = ()

    def __new__(
        cls,
        items: Iterable[_T] | MissingType = MISSING,
        /,
    ) -> Self: ...
    def __getnewargs__(self, /) -> tuple[Any, ...]: ...
    def __getstate__(self, /) -> None: ...
    def __copy__(self, /) -> Self: ...
    def __repr__(self, /) -> str: ...
    def __bool__(self, /) -> bool: ...
    def __len__(self) -> int: ...
    def copy(self, /) -> Self: ...
    def put(self, /, item: _T) -> None: ...
    async def async_put(
        self,
        /,
        item: _T,
        *,
        blocking: bool = True,
    ) -> None: ...
    def green_put(
        self,
        /,
        item: _T,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> None: ...
    async def async_get(self, /, *, blocking: bool = True) -> _T: ...
    def green_get(
        self,
        /,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> _T: ...
    @property
    def putting(self, /) -> int: ...
    @property
    def getting(self, /) -> int: ...
    @property
    def waiting(self, /) -> int: ...

class Queue(Generic[_T]):
    __slots__ = (
        "__weakref__",
        "_data",
        "_getters",
        "_maxsize",
        "_putters",
        "_putters_and_getters",
        "_unlocked",
        "_waiters",
    )

    @overload
    def __new__(cls, /, maxsize: int | None = None) -> Self: ...
    @overload
    def __new__(
        cls,
        items: Iterable[_T] | MissingType = MISSING,
        /,
        maxsize: int | None = None,
    ) -> Self: ...
    def __getnewargs__(self, /) -> tuple[Any, ...]: ...
    def __getstate__(self, /) -> None: ...
    def __copy__(self, /) -> Self: ...
    def __repr__(self, /) -> str: ...
    def __bool__(self, /) -> bool: ...
    def __len__(self) -> int: ...
    def copy(self, /) -> Self: ...
    def _acquire_nowait_on_putting(self, /) -> bool: ...
    def _acquire_nowait_on_getting(self, /) -> bool: ...
    async def _async_acquire(
        self,
        /,
        acquire_nowait: Callable[[], bool],
        waiters: deque[Event],
        *,
        blocking: bool = True,
    ) -> bool: ...
    def _green_acquire(
        self,
        /,
        acquire_nowait: Callable[[], bool],
        waiters: deque[Event],
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> bool: ...
    async def async_put(
        self,
        /,
        item: _T,
        *,
        blocking: bool = True,
    ) -> None: ...
    def green_put(
        self,
        /,
        item: _T,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> None: ...
    async def async_get(self, /, *, blocking: bool = True) -> _T: ...
    def green_get(
        self,
        /,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> _T: ...
    def _release(self, /) -> None: ...
    def _init(self, /, items: Iterable[_T], maxsize: int) -> None: ...
    def _put(self, /, item: _T) -> None: ...
    def _get(self, /) -> _T: ...
    @property
    def maxsize(self, /) -> int: ...
    @property
    def putting(self, /) -> int: ...
    @property
    def getting(self, /) -> int: ...
    @property
    def waiting(self, /) -> int: ...

class LifoQueue(Queue[_T]):
    __slots__ = ()

    @overload
    def __new__(cls, /, maxsize: int | None = None) -> Self: ...
    @overload
    def __new__(
        cls,
        items: Iterable[_T] | MissingType = MISSING,
        /,
        maxsize: int | None = None,
    ) -> Self: ...
    def __getnewargs__(self, /) -> tuple[Any, ...]: ...
    def __getstate__(self, /) -> None: ...
    def __copy__(self, /) -> Self: ...
    def __repr__(self, /) -> str: ...
    def __bool__(self, /) -> bool: ...
    def __len__(self) -> int: ...
    def copy(self, /) -> Self: ...
    async def async_put(
        self,
        /,
        item: _T,
        *,
        blocking: bool = True,
    ) -> None: ...
    def green_put(
        self,
        /,
        item: _T,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> None: ...
    async def async_get(self, /, *, blocking: bool = True) -> _T: ...
    def green_get(
        self,
        /,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> _T: ...
    def _init(self, /, items: Iterable[_T], maxsize: int) -> None: ...
    def _put(self, /, item: _T) -> None: ...
    def _get(self, /) -> _T: ...
    @property
    def maxsize(self, /) -> int: ...
    @property
    def putting(self, /) -> int: ...
    @property
    def getting(self, /) -> int: ...
    @property
    def waiting(self, /) -> int: ...

class PriorityQueue(Queue[_RichComparableT]):
    __slots__ = ()

    @overload
    def __new__(cls, /, maxsize: int | None = None) -> Self: ...
    @overload
    def __new__(
        cls,
        items: Iterable[_RichComparableT] | MissingType = MISSING,
        /,
        maxsize: int | None = None,
    ) -> Self: ...
    def __getnewargs__(self, /) -> tuple[Any, ...]: ...
    def __getstate__(self, /) -> None: ...
    def __copy__(self, /) -> Self: ...
    def __repr__(self, /) -> str: ...
    def __bool__(self, /) -> bool: ...
    def __len__(self) -> int: ...
    def copy(self, /) -> Self: ...
    async def async_put(
        self,
        /,
        item: _RichComparableT,
        *,
        blocking: bool = True,
    ) -> None: ...
    def green_put(
        self,
        /,
        item: _RichComparableT,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> None: ...
    async def async_get(
        self,
        /,
        *,
        blocking: bool = True,
    ) -> _RichComparableT: ...
    def green_get(
        self,
        /,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> _RichComparableT: ...
    def _init(
        self,
        /,
        items: Iterable[_RichComparableT],
        maxsize: int,
    ) -> None: ...
    def _put(self, /, item: _RichComparableT) -> None: ...
    def _get(self, /) -> _RichComparableT: ...
    @property
    def maxsize(self, /) -> int: ...
    @property
    def putting(self, /) -> int: ...
    @property
    def getting(self, /) -> int: ...
    @property
    def waiting(self, /) -> int: ...
