#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from types import MappingProxyType, TracebackType
from typing import Any

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

class CapacityLimiter:
    __slots__ = (
        "__weakref__",
        "_borrowers",
        "_borrowers_proxy",
        "_semaphore",
    )

    def __new__(cls, /, total_tokens: int | None = None) -> Self: ...
    def __getnewargs__(self, /) -> tuple[Any, ...]: ...
    def __getstate__(self, /) -> None: ...
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
    async def async_acquire(self, /, *, blocking: bool = True) -> bool: ...
    def green_acquire(
        self,
        /,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> bool: ...
    def async_release(self, /) -> None: ...
    def green_release(self, /) -> None: ...
    def async_borrowed(self, /) -> bool: ...
    def green_borrowed(self, /) -> bool: ...
    @property
    def total_tokens(self, /) -> int: ...
    @property
    def available_tokens(self, /) -> int: ...
    @property
    def borrowed_tokens(self, /) -> int: ...
    @property
    def borrowers(self, /) -> MappingProxyType[tuple[str, int], int]: ...
    @property
    def waiting(self, /) -> int: ...

class RCapacityLimiter(CapacityLimiter):
    __slots__ = ()

    async def async_acquire(
        self,
        /,
        count: int = 1,
        *,
        blocking: bool = True,
    ) -> bool: ...
    def green_acquire(
        self,
        /,
        count: int = 1,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> bool: ...
    def async_release(self, /, count: int = 1) -> None: ...
    def green_release(self, /, count: int = 1) -> None: ...
    def async_count(self, /) -> int: ...
    def green_count(self, /) -> int: ...
