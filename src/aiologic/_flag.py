#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from typing import TYPE_CHECKING, Any, Generic, TypeVar

from .meta import MISSING, MissingType

if sys.version_info >= (3, 13):
    from typing import TypeVar
else:
    from typing_extensions import TypeVar

if sys.version_info >= (3, 11):
    from typing import overload
else:
    from typing_extensions import overload

if TYPE_CHECKING:
    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self

    if sys.version_info >= (3, 9):
        from collections.abc import Callable
    else:
        from typing import Callable

_T = TypeVar("_T", default=object)
_D = TypeVar("_D")


class Flag(Generic[_T]):
    """..."""

    __slots__ = (
        "__weakref__",
        "_markers",
    )

    def __new__(cls, /, marker: _T | MissingType = MISSING) -> Self:
        """..."""

        self = object.__new__(cls)

        if marker is not MISSING:
            self._markers = [marker]
        else:
            self._markers = []

        return self

    def __getnewargs__(self, /) -> tuple[Any, ...]:
        """
        Returns arguments that can be used to create new instances with the
        same state.

        Used by:

        * The :mod:`pickle` module for pickling.
        * The :mod:`copy` module for copying.

        The current state affects the arguments.

        Example:
            >>> orig = Flag()
            >>> orig.set('value')  # change the state
            >>> orig.get()
            'value'
            >>> copy = Flag(*orig.__getnewargs__())
            >>> copy.get()
            'value'
        """

        marker = MISSING

        if self._markers:
            try:
                marker = self._markers[0]
            except IndexError:
                pass

        if marker is MISSING:
            return ()

        return (marker,)

    def __getstate__(self, /) -> None:
        """
        Disables the use of internal state for pickling and copying.
        """

        return None

    def __copy__(self, /) -> Self:
        """..."""

        marker = MISSING

        if self._markers:
            try:
                marker = self._markers[0]
            except IndexError:
                pass

        return self.__class__(marker)

    def __repr__(self, /) -> str:
        """..."""

        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        marker = MISSING

        if self._markers:
            try:
                marker = self._markers[0]
            except IndexError:
                pass

        if marker is MISSING:
            return f"{cls_repr}()"

        return f"{cls_repr}({marker!r})"

    def __bool__(self, /) -> bool:
        """
        Returns :data:`True` if the flag is set.

        Used by the standard :ref:`truth testing procedure <truth>`.

        Example:
            >>> cancelled = Flag()  # flag is unset
            >>> bool(cancelled)
            False
            >>> cancelled.set()  # flag is set
            >>> bool(cancelled)
            True
        """

        return bool(self._markers)

    def copy(self, /) -> Self:
        """..."""

        return self.__copy__()

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
    def get(self, /, default=MISSING, *, default_factory=MISSING):
        """..."""

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
        """..."""

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
        """..."""

        self._markers.clear()
