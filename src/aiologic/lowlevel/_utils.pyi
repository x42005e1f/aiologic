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

_F = TypeVar("_F", bound=Callable[..., Any])
_T = TypeVar("_T")
_P = ParamSpec("_P")

def _external(func: _F, /) -> _F: ...
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
@overload
def _copies(
    original: Callable[_P, _T],
    wrapper: None = None,
    /,
) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]: ...
@overload
def _copies(
    original: Callable[_P, _T],
    wrapper: Callable[_P, _T],
    /,
) -> Callable[_P, _T]: ...
