#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys
import warnings

from typing import TYPE_CHECKING, Any

import aiologic._flag

from ._markers import MISSING, MissingType

if sys.version_info >= (3, 13):
    from typing import TypeVar
else:
    from typing_extensions import TypeVar

if TYPE_CHECKING:
    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self

_T = TypeVar("_T", default=object)


class Flag(aiologic._flag.Flag[_T]):
    __slots__ = ()

    def __new__(cls, /, marker: _T | MissingType = MISSING) -> Self:
        warnings.warn("Use aiologic.Flag instead", DeprecationWarning, 1)

        self = object.__new__(cls)

        if marker is not MISSING:
            self._markers = [marker]
        else:
            self._markers = []

        return self

    def __init_subclass__(cls, /, **kwargs: Any) -> None:
        warnings.warn("Use aiologic.Flag instead", DeprecationWarning, 1)

        super().__init_subclass__(**kwargs)

    def __reduce__(self, /) -> tuple[Any, ...]:
        if self._markers:
            try:
                return (aiologic.Flag, (self._markers[0],))
            except IndexError:
                pass

        return (aiologic.Flag, ())
