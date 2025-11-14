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

if TYPE_CHECKING:
    if sys.version_info >= (3, 9):
        from collections.abc import Callable
    else:
        from typing import Callable

_T = TypeVar("_T")
_P = ParamSpec("_P")


@overload
def replaces(
    namespace: dict[str, Any],
    wrapper: MissingType = MISSING,
    /,
) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]: ...
@overload
def replaces(
    namespace: dict[str, Any],
    wrapper: Callable[_P, _T],
    /,
) -> Callable[_P, _T]: ...
def replaces(namespace, wrapper=MISSING, /):
    """
    Wrap and replace the function of the same name in *namespace*.

    Used for global rebinding.

    Unlike :func:`functools.wraps`, excludes the ``__wrapped__`` attribute to
    avoid memory leaks in a multithreaded environment.

    Example:
      >>> def sketch():
      ...     return 'parrot'
      >>> def replace_sketch():
      ...     @replaces(globals())
      ...     def sketch():
      ...         return 'ex-parrot'
      >>> sketch()
      'parrot'
      >>> replace_sketch()
      >>> sketch()
      'ex-parrot'
    """

    if wrapper is MISSING:
        return partial(replaces, namespace)

    wrapper = update_wrapper(wrapper, namespace[wrapper.__name__])

    del wrapper.__wrapped__

    namespace[wrapper.__name__] = wrapper

    return wrapper


@overload
def copies(
    original: Callable[_P, _T],
    wrapper: MissingType = MISSING,
    /,
) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]: ...
@overload
def copies(
    original: Callable[_P, _T],
    wrapper: Callable[_P, _T],
    /,
) -> Callable[_P, _T]: ...
def copies(original, wrapper=MISSING, /):
    """
    Replace with a copy of *original* if that is a Python level function.

    Used to optimize functions which delegate all the work to others.

    Does nothing on type checking.

    Example:
      >>> def sig1():
      ...     return 42
      >>> @copies(sig1)
      ... def sig2():
      ...     return sig1()
      >>> sig1()
      42
      >>> sig2()
      42
      >>> sig1 is sig2
      False
      >>> sig1.__code__ is sig2.__code__
      True
    """

    if wrapper is MISSING:
        return partial(copies, original)

    if isinstance(original, FunctionType) and not TYPE_CHECKING:
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
