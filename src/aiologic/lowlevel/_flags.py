#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from typing import TYPE_CHECKING, Any, Generic, TypeVar, overload

import aiologic

from ._markers import MISSING, MissingType

if sys.version_info >= (3, 13):
    from warnings import deprecated
else:
    from typing_extensions import deprecated

if TYPE_CHECKING:
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

    @deprecated("Use aiologic.Flag instead")
    def __new__(cls, /, marker: _T | MissingType = MISSING) -> Self:
        self = super().__new__(cls)

        if marker is not MISSING:
            self.__markers = [marker]
        else:
            self.__markers = []

        return self

    def __reduce__(self, /) -> tuple[Any, ...]:
        if self.__markers:
            try:
                return (aiologic.Flag, (self.__markers[0],))
            except IndexError:
                pass

        return (aiologic.Flag, ())

    def __repr__(self, /) -> str:
        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        if self.__markers:
            try:
                return f"{cls_repr}({self.__markers[0]!r})"
            except IndexError:
                pass

        return f"{cls_repr}()"

    def __bool__(self, /) -> bool:
        return bool(self.__markers)

    @overload
    def get(
        self,
        /,
        default: _T | MissingType,
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
    def get(self, /, default=MISSING, *, default_factory=MISSING):
        if self.__markers:
            try:
                return self.__markers[0]
            except IndexError:
                pass

        if default is not MISSING:
            return default

        if default_factory is not MISSING:
            return default_factory()

        raise LookupError(self)

    @overload
    def set(self: Flag[object], /, marker: MissingType = MISSING) -> bool: ...
    @overload
    def set(self, /, marker: _T) -> bool: ...
    def set(self, /, marker=MISSING):
        markers = self.__markers

        if not markers:
            if marker is MISSING:
                marker = object()

            markers.append(marker)

            if len(markers) > 1:
                del markers[1:]

        if marker is not MISSING:
            try:
                return marker is markers[0]
            except IndexError:
                pass

        return False

    def clear(self, /) -> None:
        self.__markers.clear()
