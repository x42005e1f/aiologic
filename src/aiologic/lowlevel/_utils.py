#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from functools import partial, update_wrapper
from typing import TYPE_CHECKING, Any, TypeVar, overload

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


def _external(func: _F, /) -> _F:
    if not TYPE_CHECKING:
        func.__module__ = func.__module__.rpartition(".")[0]

    return func


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
def _replaces(namespace, wrapper=None, /):
    if wrapper is None:
        return partial(_replaces, namespace)

    wrapper = update_wrapper(wrapper, namespace[wrapper.__name__])

    del wrapper.__wrapped__

    namespace[wrapper.__name__] = wrapper

    return wrapper
