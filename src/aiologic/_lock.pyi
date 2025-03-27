#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from types import TracebackType

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

class PLock:
    def __new__(cls, /) -> Self: ...
    def __bool__(self, /) -> bool: ...
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
    def async_release(self, /) -> None: ...
    def green_release(self, /) -> None: ...
    def locked(self, /) -> bool: ...
    @property
    def waiting(self, /) -> int: ...

class BLock(PLock): ...

class Lock(PLock):
    @property
    def owner(self, /) -> tuple[str, int] | None: ...

class RLock(PLock):
    @property
    def owner(self, /) -> tuple[str, int] | None: ...
    @property
    def level(self, /) -> int: ...
