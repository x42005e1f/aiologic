#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from typing import Final, Literal, final

@final
class MissingType:
    def __new__(cls, /) -> MissingType: ...
    def __bool__(self, /) -> Literal[False]: ...

MISSING: Final[MissingType]
