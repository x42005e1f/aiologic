#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from types import TracebackType

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

class CapacityLimiter:
    def __new__(cls, /, total_tokens: int) -> Self: ...
    async def __aenter__(self, /) -> Self: ...
    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...
    def __enter__(self, /) -> Self: ...
    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...
    async def async_acquire_on_behalf_of(
        self,
        /,
        borrower: object,
        *,
        blocking: bool = True,
    ) -> bool: ...
    async def async_acquire(self, /, *, blocking: bool = True) -> bool: ...
    def green_acquire_on_behalf_of(
        self,
        /,
        borrower: object,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> bool: ...
    def green_acquire(
        self,
        /,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> bool: ...
    def async_release_on_behalf_of(self, /, borrower: object) -> None: ...
    def async_release(self, /) -> None: ...
    def green_release_on_behalf_of(self, /, borrower: object) -> None: ...
    def green_release(self, /) -> None: ...
    @property
    def borrowers(self, /) -> set[object]: ...
    @property
    def waiting(self, /) -> int: ...
    @property
    def available_tokens(self, /) -> int: ...
    @property
    def borrowed_tokens(self, /) -> int: ...
    @property
    def total_tokens(self, /) -> int: ...

class RCapacityLimiter:
    def __new__(cls, /, total_tokens: int) -> Self: ...
    async def __aenter__(self, /) -> Self: ...
    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...
    def __enter__(self, /) -> Self: ...
    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...
    async def async_acquire_on_behalf_of(
        self,
        /,
        borrower: object,
        *,
        blocking: bool = True,
    ) -> bool: ...
    async def async_acquire(self, /, *, blocking: bool = True) -> bool: ...
    def green_acquire_on_behalf_of(
        self,
        /,
        borrower: object,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> bool: ...
    def green_acquire(
        self,
        /,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> bool: ...
    def async_release_on_behalf_of(self, /, borrower: object) -> None: ...
    def async_release(self, /) -> None: ...
    def green_release_on_behalf_of(self, /, borrower: object) -> None: ...
    def green_release(self, /) -> None: ...
    @property
    def borrowers(self, /) -> dict[object, int]: ...
    @property
    def waiting(self, /) -> int: ...
    @property
    def available_tokens(self, /) -> int: ...
    @property
    def borrowed_tokens(self, /) -> int: ...
    @property
    def total_tokens(self, /) -> int: ...
