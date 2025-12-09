#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import enum
import sys

from typing import Final, NoReturn

if sys.version_info >= (3, 11):  # a caching bug fix
    from typing import Literal
else:  # typing-extensions>=4.6.0
    from typing_extensions import Literal

if sys.version_info >= (3, 11):  # runtime introspection support
    from typing import final
else:  # typing-extensions>=4.1.0
    from typing_extensions import final

class SingletonEnum(enum.Enum):  # type: ignore[misc]
    def __setattr__(self, /, name: str, value: object) -> None: ...
    def __repr__(self, /) -> str: ...
    def __str__(self, /) -> str: ...

@final
class DefaultType(SingletonEnum):
    DEFAULT = "DEFAULT"

    def __init_subclass__(cls, /, **kwargs: object) -> NoReturn: ...
    def __bool__(self, /) -> Literal[False]: ...

@final
class MissingType(SingletonEnum):
    MISSING = "MISSING"

    def __init_subclass__(cls, /, **kwargs: object) -> NoReturn: ...
    def __bool__(self, /) -> Literal[False]: ...

DEFAULT: Final[Literal[DefaultType.DEFAULT]]
MISSING: Final[Literal[MissingType.MISSING]]
