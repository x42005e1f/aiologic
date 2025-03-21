#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from collections.abc import Awaitable
from typing import Callable, TypeVar, overload

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

_T = TypeVar("_T")
_P = ParamSpec("_P")

@overload
def shield(wrapped: Awaitable[_T], /) -> Awaitable[_T]: ...
@overload
def shield(wrapped: Callable[_P, _T], /) -> Callable[_P, _T]: ...
