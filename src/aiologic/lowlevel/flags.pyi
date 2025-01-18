#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from typing import Callable, Generic, TypeVar, overload

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

_T = TypeVar("_T")
_D = TypeVar("_D")

class Flag(Generic[_T]):
    @overload
    def __new__(cls, /) -> Self: ...
    @overload
    def __new__(cls, /, marker: _T) -> Self: ...
    def __bool__(self, /) -> bool: ...
    @overload
    def get(self, /) -> _T: ...
    @overload
    def get(self, /, default: _T) -> _T: ...
    @overload
    def get(self, /, default: _D) -> _T | _D: ...
    @overload
    def get(self, /, *, default_factory: Callable[[], _T]) -> _T: ...
    @overload
    def get(self, /, *, default_factory: Callable[[], _D]) -> _T | _D: ...
    @overload
    def set(self, /) -> bool: ...
    @overload
    def set(self, /, marker: _T) -> bool: ...
    def clear(self, /) -> None: ...
