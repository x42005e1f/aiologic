#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from typing import Any, TypeVar

import aiologic._flag

if sys.version_info >= (3, 13):
    from warnings import deprecated
else:
    from typing_extensions import deprecated

_T = TypeVar("_T")


@deprecated("Use aiologic.Flag instead")
class Flag(aiologic._flag.Flag[_T]):
    __slots__ = ()

    def __reduce__(self, /) -> tuple[Any, ...]:
        if self._markers:
            try:
                return (aiologic.Flag, (self._markers[0],))
            except IndexError:
                pass

        return (aiologic.Flag, ())
