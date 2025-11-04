#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from typing import Any, Generic

from .meta import MISSING, MissingType

if sys.version_info >= (3, 13):
    from typing import TypeVar
else:
    from typing_extensions import TypeVar

if sys.version_info >= (3, 11):
    from typing import Self, overload
else:
    from typing_extensions import Self, overload

if sys.version_info >= (3, 9):
    from collections.abc import Callable
else:
    from typing import Callable

_T = TypeVar("_T", default=object)
_D = TypeVar("_D")

class Flag(Generic[_T]):
    __slots__ = (
        "__weakref__",
        "_markers",
    )

    def __new__(cls, /, marker: _T | MissingType = MISSING) -> Self: ...
    def __getnewargs__(self, /) -> tuple[Any, ...]: ...
    def __getstate__(self, /) -> None: ...
    def __copy__(self, /) -> Self: ...
    def __repr__(self, /) -> str: ...
    def __bool__(self, /) -> bool: ...
    def copy(self, /) -> Self: ...
    @overload
    def get(
        self,
        /,
        default: _T | MissingType = MISSING,
        *,
        default_factory: MissingType = MISSING,
    ) -> _T: ...
    @overload
    def get(
        self,
        /,
        default: _D,
        *,
        default_factory: MissingType = MISSING,
    ) -> _T | _D: ...
    @overload
    def get(
        self,
        /,
        default: MissingType = MISSING,
        *,
        default_factory: Callable[[], _T],
    ) -> _T: ...
    @overload
    def get(
        self,
        /,
        default: MissingType = MISSING,
        *,
        default_factory: Callable[[], _D],
    ) -> _T | _D: ...
    @overload
    def set(self: Flag[object], /, marker: MissingType = MISSING) -> bool: ...
    @overload
    def set(self, /, marker: _T) -> bool: ...
    def clear(self, /) -> None: ...
