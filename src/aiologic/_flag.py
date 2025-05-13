#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar, overload

from .lowlevel._markers import MISSING, MissingType

if TYPE_CHECKING:
    import sys

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
    __slots__ = (
        "__weakref__",
        "_markers",
    )

    def __new__(cls, /, marker: _T | MissingType = MISSING) -> Self:
        self = super().__new__(cls)

        if marker is not MISSING:
            self._markers = [marker]
        else:
            self._markers = []

        return self

    def __getnewargs__(self, /) -> tuple[Any, ...]:
        if self._markers:
            try:
                return (self._markers[0],)
            except IndexError:
                pass

        return ()

    def __getstate__(self, /) -> None:
        return None

    def __repr__(self, /) -> str:
        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        if self._markers:
            try:
                return f"{cls_repr}({self._markers[0]!r})"
            except IndexError:
                pass

        return f"{cls_repr}()"

    def __bool__(self, /) -> bool:
        return bool(self._markers)

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
        if self._markers:
            try:
                return self._markers[0]
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
        markers = self._markers

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
        self._markers.clear()
