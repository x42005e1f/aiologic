#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from typing import Any, Generic, TypeVar, overload

from ._markers import MissingType

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if sys.version_info >= (3, 9):
    from collections.abc import Callable
else:
    from typing import Callable

_T = TypeVar("_T")
_D = TypeVar("_D")

class Flag(Generic[_T]):
    __slots__ = ("__markers",)

    def __new__(cls, /, marker: _T | MissingType = ...) -> Self: ...
    def __getnewargs__(self, /) -> tuple[Any, ...]: ...
    def __bool__(self, /) -> bool: ...
    @overload
    def get(
        self,
        /,
        default: _T | MissingType,
        *,
        default_factory: MissingType = ...,
    ) -> _T: ...
    @overload
    def get(
        self,
        /,
        default: _D,
        *,
        default_factory: MissingType = ...,
    ) -> _T | _D: ...
    @overload
    def get(
        self,
        /,
        default: MissingType = ...,
        *,
        default_factory: Callable[[], _T],
    ) -> _T: ...
    @overload
    def get(
        self,
        /,
        default: MissingType = ...,
        *,
        default_factory: Callable[[], _D],
    ) -> _T | _D: ...
    @overload
    def set(self: Flag[object], /, marker: MissingType = ...) -> bool: ...
    @overload
    def set(self, /, marker: _T) -> bool: ...
    def clear(self, /) -> None: ...
