#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from typing import Any, TypeVar, overload

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

if sys.version_info >= (3, 9):
    from collections.abc import Callable
else:
    from typing import Callable

_T = TypeVar("_T")
_P = ParamSpec("_P")

@overload
def _replaces(
    namespace: dict[str, Any],
    wrapper: None = None,
    /,
) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]: ...
@overload
def _replaces(
    namespace: dict[str, Any],
    wrapper: Callable[_P, _T],
    /,
) -> Callable[_P, _T]: ...
