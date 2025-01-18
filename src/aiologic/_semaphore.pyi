#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from types import TracebackType

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

class Semaphore:
    def __new__(
        cls,
        /,
        initial_value: int | None = None,
        max_value: int | None = None,
    ) -> Self: ...
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
    def waiting(self, /) -> int: ...
    @property
    def value(self, /) -> int: ...
    @property
    def initial_value(self, /) -> int: ...

class BoundedSemaphore:
    def __new__(
        cls,
        /,
        initial_value: int | None = None,
        max_value: int | None = None,
    ) -> Self: ...
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
    def waiting(self, /) -> int: ...
    @property
    def value(self, /) -> int: ...
    @property
    def initial_value(self, /) -> int: ...
    @property
    def max_value(self, /) -> int: ...
