#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from typing import Any

import aiologic._flag

from ._markers import MISSING, MissingType

if sys.version_info >= (3, 13):
    from typing import TypeVar
    from warnings import deprecated
else:
    from typing_extensions import TypeVar, deprecated

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

_T = TypeVar("_T", default=object)

@deprecated("Use aiologic.Flag instead")
class Flag(aiologic._flag.Flag[_T]):
    __slots__ = ()

    def __new__(cls, /, marker: _T | MissingType = MISSING) -> Self: ...
    def __init_subclass__(cls, /, **kwargs: Any) -> None: ...
    def __reduce__(self, /) -> tuple[Any, ...]: ...
