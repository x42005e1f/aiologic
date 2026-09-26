#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import enum

from typing import Any, Final, Literal, Never, final

class _SingletonMeta(enum.EnumType): ...

class SingletonEnum(enum.Enum, metaclass=_SingletonMeta):  # type: ignore[misc]
    def __repr__(self, /) -> str: ...
    def __str__(self, /) -> str: ...

@final
class DefaultType(SingletonEnum):
    DEFAULT = "DEFAULT"

    def __init_subclass__(cls, /, **kwargs: Any) -> Never: ...
    def __bool__(self, /) -> Literal[False]: ...

@final
class MissingType(SingletonEnum):
    MISSING = "MISSING"

    def __init_subclass__(cls, /, **kwargs: Any) -> Never: ...
    def __bool__(self, /) -> Literal[False]: ...

DEFAULT: Final[Literal[DefaultType.DEFAULT]]
MISSING: Final[Literal[MissingType.MISSING]]
