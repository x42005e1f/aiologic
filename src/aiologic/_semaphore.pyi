#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from types import TracebackType
from typing import Any, Final, overload

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

_USE_DELATTR: Final[bool]
_USE_BYTEARRAY: Final[bool]

_PERFECT_FAIRNESS_ENABLED: Final[bool]

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
        initial_value: int | None = None,
        max_value: None = None,
    ) -> Self: ...
    @overload
    def __new__(
        cls,
        /,
        initial_value: int | None,
        max_value: int,
    ) -> BoundedSemaphore: ...
    @overload
    def __new__(cls, /, *, max_value: int) -> BoundedSemaphore: ...
    def __getnewargs__(self, /) -> tuple[Any, ...]: ...
    def __getstate__(self, /) -> None: ...
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
    async def async_acquire(self, /, *, blocking: bool = True) -> bool: ...
    def green_acquire(
        self,
        /,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> bool: ...
    def release(self, /, count: int = 1) -> None: ...

    async_release = release
    green_release = release
    _async_acquire = async_acquire
    _green_acquire = green_acquire
    _release = release

    @property
    def initial_value(self, /) -> int: ...
    @property
    def value(self, /) -> int: ...
    @value.setter
    def value(self, /, value: int) -> None: ...
    @property
    def waiting(self, /) -> int: ...

class BoundedSemaphore(Semaphore):
    __slots__ = (
        "_locked",
        "_max_value",
    )

    @overload
    def __new__(
        cls,
        /,
        initial_value: int | None = None,
        max_value: None = None,
    ) -> Self: ...
    @overload
    def __new__(
        cls,
        /,
        initial_value: int | None,
        max_value: int,
    ) -> Self: ...
    @overload
    def __new__(cls, /, *, max_value: int) -> Self: ...
    def __getnewargs__(self, /) -> tuple[Any, ...]: ...
    def __getstate__(self, /) -> None: ...
    async def async_acquire(self, /, *, blocking: bool = True) -> bool: ...
    def green_acquire(
        self,
        /,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> bool: ...
    def release(self, /, count: int = 1) -> None: ...

    async_release = release
    green_release = release

    @property
    def max_value(self, /) -> int: ...
    @property
    def value(self, /) -> int: ...
    @value.setter
    def value(self, /, value: int) -> None: ...
