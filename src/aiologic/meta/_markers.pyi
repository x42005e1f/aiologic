#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import enum

from typing import Final, Literal, NoReturn, final

class SingletonEnum(enum.Enum):  # type: ignore[misc]
    __slots__ = ()

    def __setattr__(self, /, name: str, value: object) -> None: ...
    def __repr__(self, /) -> str: ...
    def __str__(self, /) -> str: ...

@final
class DefaultType(SingletonEnum):
    __slots__ = ()

    DEFAULT = "DEFAULT"

    def __init_subclass__(cls, /, **kwargs: object) -> NoReturn: ...
    def __bool__(self, /) -> Literal[False]: ...

@final
class MissingType(SingletonEnum):
    __slots__ = ()

    MISSING = "MISSING"

    def __init_subclass__(cls, /, **kwargs: object) -> NoReturn: ...
    def __bool__(self, /) -> Literal[False]: ...

DEFAULT: Final[Literal[DefaultType.DEFAULT]]
MISSING: Final[Literal[MissingType.MISSING]]
