#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from types import TracebackType
from typing import Any, Final

from .lowlevel import Event
from .meta import DEFAULT, DefaultType

if sys.version_info >= (3, 11):
    from typing import Self, overload
else:
    from typing_extensions import Self, overload

_USE_DELATTR: Final[bool]
_USE_BYTEARRAY: Final[bool]

_PERFECT_FAIRNESS_ENABLED: Final[bool]

_USE_ONCELOCK: Final[bool]

class Semaphore:
    __slots__ = (
        "__weakref__",
        "_initial_value",
        "_unlocked",
        "_waiters",
    )

    @overload
    def __new__(
        cls,
        /,
        initial_value: int | DefaultType = DEFAULT,
        max_value: None = None,
    ) -> Self: ...
    @overload
    def __new__(
        cls,
        /,
        initial_value: int | DefaultType,
        max_value: int | DefaultType,
    ) -> BoundedSemaphore: ...
    @overload
    def __new__(
        cls,
        /,
        *,
        max_value: int | DefaultType,
    ) -> BoundedSemaphore: ...
    def __getnewargs__(self, /) -> tuple[Any, ...]: ...
    def __getstate__(self, /) -> None: ...
    def __copy__(self, /) -> Self: ...
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
    def _acquire_nowait(self, /) -> bool: ...
    async def _async_acquire(
        self,
        /,
        *,
        blocking: bool = True,
        _shield: bool = False,
    ) -> bool: ...
    def _green_acquire(
        self,
        /,
        *,
        blocking: bool = True,
        timeout: float | None = None,
        _shield: bool = False,
    ) -> bool: ...
    async def async_acquire(self, /, *, blocking: bool = True) -> bool: ...
    def green_acquire(
        self,
        /,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> bool: ...
    def _release(self, /, count: int = 1) -> None: ...
    def release(self, /, count: int = 1) -> None: ...
    def async_release(self, /, count: int = 1) -> None: ...
    def green_release(self, /, count: int = 1) -> None: ...
    @property
    def initial_value(self, /) -> int: ...
    @property
    def value(self, /) -> int: ...
    @property
    def waiting(self, /) -> int: ...

class BoundedSemaphore(Semaphore):
    __slots__ = (
        "_locked",
        "_max_value",
    )

    def __new__(
        cls,
        /,
        initial_value: int | DefaultType = DEFAULT,
        max_value: int | DefaultType = DEFAULT,
    ) -> Self: ...
    def __getnewargs__(self, /) -> tuple[Any, ...]: ...
    def __getstate__(self, /) -> None: ...
    def __copy__(self, /) -> Self: ...
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
    async def async_acquire(self, /, *, blocking: bool = True) -> bool: ...
    def green_acquire(
        self,
        /,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> bool: ...
    def release(self, /, count: int = 1) -> None: ...
    def async_release(self, /, count: int = 1) -> None: ...
    def green_release(self, /, count: int = 1) -> None: ...
    @property
    def initial_value(self, /) -> int: ...
    @property
    def max_value(self, /) -> int: ...
    @property
    def value(self, /) -> int: ...
    @property
    def waiting(self, /) -> int: ...

class BinarySemaphore(Semaphore):
    __slots__ = ()

    @overload
    def __new__(
        cls,
        /,
        initial_value: int | DefaultType = DEFAULT,
        max_value: None = None,
    ) -> Self: ...
    @overload
    def __new__(
        cls,
        /,
        initial_value: int | DefaultType,
        max_value: int | DefaultType,
    ) -> BoundedBinarySemaphore: ...
    @overload
    def __new__(
        cls,
        /,
        *,
        max_value: int | DefaultType,
    ) -> BoundedBinarySemaphore: ...
    def __getnewargs__(self, /) -> tuple[Any, ...]: ...
    def __getstate__(self, /) -> None: ...
    def __copy__(self, /) -> Self: ...
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
    async def async_acquire(self, /, *, blocking: bool = True) -> bool: ...
    def green_acquire(
        self,
        /,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> bool: ...
    def _release(self, /, count: int = 1) -> None: ...
    def release(self, /, count: int = 1) -> None: ...
    def async_release(self, /, count: int = 1) -> None: ...
    def green_release(self, /, count: int = 1) -> None: ...
    @property
    def initial_value(self, /) -> int: ...
    @property
    def value(self, /) -> int: ...
    @property
    def waiting(self, /) -> int: ...

    # Internal methods used by condition variables

    def _park(self, /, token: list[Any]) -> bool: ...
    def _unpark(self, /, event: Event) -> None: ...
    def _after_park(self, /) -> None: ...

class BoundedBinarySemaphore(BinarySemaphore, BoundedSemaphore):
    __slots__ = ()

    def __new__(
        cls,
        /,
        initial_value: int | DefaultType = DEFAULT,
        max_value: int | DefaultType = DEFAULT,
    ) -> Self: ...
    def __getnewargs__(self, /) -> tuple[Any, ...]: ...
    def __getstate__(self, /) -> None: ...
    def __copy__(self, /) -> Self: ...
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
    async def async_acquire(self, /, *, blocking: bool = True) -> bool: ...
    def green_acquire(
        self,
        /,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> bool: ...
    def release(self, /, count: int = 1) -> None: ...
    def async_release(self, /, count: int = 1) -> None: ...
    def green_release(self, /, count: int = 1) -> None: ...
    @property
    def initial_value(self, /) -> int: ...
    @property
    def max_value(self, /) -> int: ...
    @property
    def value(self, /) -> int: ...
    @property
    def waiting(self, /) -> int: ...

    # Internal methods used by condition variables

    def _after_park(self, /) -> None: ...
