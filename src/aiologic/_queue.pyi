#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from collections.abc import Iterable
from typing import Generic, TypeVar, overload

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

_T = TypeVar("_T")

class QueueEmpty(Exception): ...
class QueueFull(Exception): ...

class SimpleQueue(Generic[_T]):
    @overload
    def __new__(cls, /) -> Self: ...
    @overload
    def __new__(cls, items: Iterable[_T], /) -> Self: ...
    def __bool__(self, /) -> bool: ...
    def __len__(self) -> int: ...
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
    async def async_get(
        self,
        /,
        *,
        blocking: bool = True,
    ) -> _T: ...
    def green_get(
        self,
        /,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> _T: ...
    @property
    def waiting(self, /) -> int: ...
    @property
    def putting(self, /) -> int: ...
    @property
    def getting(self, /) -> int: ...

class Queue(Generic[_T]):
    @overload
    def __new__(cls, /, maxsize: int | None = None) -> Self: ...
    @overload
    def __new__(
        cls,
        items: Iterable[_T],
        /,
        maxsize: int | None = None,
    ) -> Self: ...
    def __bool__(self, /) -> bool: ...
    def __len__(self) -> int: ...
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
    async def async_get(
        self,
        /,
        *,
        blocking: bool = True,
    ) -> _T: ...
    def green_get(
        self,
        /,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> _T: ...
    @property
    def waiting(self, /) -> int: ...
    @property
    def putting(self, /) -> int: ...
    @property
    def getting(self, /) -> int: ...
    @property
    def maxsize(self, /) -> int: ...

class LifoQueue(Queue[_T]): ...
class PriorityQueue(Queue[_T]): ...
