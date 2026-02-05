#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import enum
import sys

from typing import Any, Final

if sys.version_info >= (3, 11):  # python/cpython#22392 | python/cpython#93064
    from enum import EnumType
else:
    from enum import EnumMeta as EnumType

if sys.version_info >= (3, 9):  # various bug fixes (caching, etc.)
    from typing import Literal
else:  # typing-extensions>=4.6.0
    from typing_extensions import Literal

if sys.version_info >= (3, 11):  # python/cpython#30842
    from typing import Never
else:  # typing-extensions>=4.1.0
    from typing_extensions import Never

if sys.version_info >= (3, 11):  # python/cpython#30530: introspectable
    from typing import final
else:  # typing-extensions>=4.1.0
    from typing_extensions import final

# `_SingletonMeta.__call__()` is omitted due to python/typing#270
class _SingletonMeta(EnumType): ...

# `SingletonEnum.__setattr__()` is omitted due to python/mypy#18325
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
