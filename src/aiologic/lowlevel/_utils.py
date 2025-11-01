#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from functools import partial, update_wrapper
from types import FunctionType
from typing import TYPE_CHECKING, Any, TypeVar

from ._markers import MISSING, MissingType

if sys.version_info >= (3, 11):
    from typing import overload
else:
    from typing_extensions import overload

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
    wrapper: MissingType = MISSING,
    /,
) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]: ...
@overload
def _replaces(
    namespace: dict[str, Any],
    wrapper: Callable[_P, _T],
    /,
) -> Callable[_P, _T]: ...
def _replaces(namespace, wrapper=MISSING, /):
    if wrapper is MISSING:
        return partial(_replaces, namespace)

    wrapper = update_wrapper(wrapper, namespace[wrapper.__name__])

    del wrapper.__wrapped__

    namespace[wrapper.__name__] = wrapper

    return wrapper


@overload
def _copies(
    original: Callable[_P, _T],
    wrapper: MissingType = MISSING,
    /,
) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]: ...
@overload
def _copies(
    original: Callable[_P, _T],
    wrapper: Callable[_P, _T],
    /,
) -> Callable[_P, _T]: ...
def _copies(original, wrapper=MISSING, /):
    if wrapper is MISSING:
        return partial(_copies, original)

    if not TYPE_CHECKING:
        copy = FunctionType(
            original.__code__,
            original.__globals__,
            original.__name__,
            original.__defaults__,
            original.__closure__,
        )
        copy = update_wrapper(copy, wrapper)
        copy.__kwdefaults__ = wrapper.__kwdefaults__  # python/cpython#112640

        return copy

    return wrapper
