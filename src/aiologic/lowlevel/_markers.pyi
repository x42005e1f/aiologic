#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import enum

from typing import Any, Final, Literal, NoReturn, final

@final
class MissingType(enum.Enum):
    __slots__ = ()

    MISSING = "MISSING"

    def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn: ...
    def __setattr__(self, /, name: str, value: Any) -> None: ...
    def __repr__(self, /) -> str: ...
    def __str__(self, /) -> str: ...
    def __bool__(self, /) -> Literal[False]: ...

MISSING: Final[Literal[MissingType.MISSING]]
