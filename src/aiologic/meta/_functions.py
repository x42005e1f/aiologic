#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from functools import partial, update_wrapper
from types import FunctionType
from typing import TYPE_CHECKING

from ._markers import MISSING

if TYPE_CHECKING:
    from typing import TypeVar

    from ._markers import MissingType

    if sys.version_info >= (3, 9):  # PEP 585
        from collections.abc import Callable, MutableMapping
    else:
        from typing import Callable, MutableMapping

    if sys.version_info >= (3, 10):  # PEP 612
        from typing import ParamSpec
    else:  # typing-extensions>=3.10.0
        from typing_extensions import ParamSpec

if sys.version_info >= (3, 11):  # runtime introspection support
    from typing import overload
else:  # typing-extensions>=4.2.0
    from typing_extensions import overload

if TYPE_CHECKING:
    _T = TypeVar("_T")
    _P = ParamSpec("_P")


@overload
def replaces(
    namespace: MutableMapping[str, object],
    replacer: MissingType = MISSING,
    /,
) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]: ...
@overload
def replaces(
    namespace: MutableMapping[str, object],
    replacer: Callable[_P, _T],
    /,
) -> Callable[_P, _T]: ...
def replaces(namespace, replacer=MISSING, /):
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

    if replacer is MISSING:
        return partial(replaces, namespace)

    # The replaced function may have a different `__name__` attribute value
    # than the replacer, so we must always use the name obtained before
    # wrapping.
    name = replacer.__name__

    # When `update_wrapper()` is applied sequentially (a special case of
    # parallel calls) on the same namespace to functions of the same name, they
    # will refer to each other via the `__wrapped__` attribute, which will
    # prevent them from being deleted from memory. Therefore, we delete the
    # attribute after the call to break the reference chain.
    update_wrapper(replacer, namespace[name])

    # Usually, the decorator is called for a newly defined function, but it can
    # also be used in parallel for older ones, so we have to handle concurrent
    # attempts to delete the attribute.
    try:
        del replacer.__wrapped__
    except AttributeError:  # already deleted
        pass

    namespace[name] = replacer

    return replacer


@overload
def copies(
    original: Callable[_P, _T],
    replaced: MissingType = MISSING,
    /,
) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]: ...
@overload
def copies(
    original: Callable[_P, _T],
    replaced: Callable[_P, _T],
    /,
) -> Callable[_P, _T]: ...
def copies(original, replaced=MISSING, /):
    """
    Replace with a copy of *original* if that is a user-defined function, and
    make the copy look like *replaced* function.

    Used to optimize functions which delegate all the work to others.

    Does nothing on type checking.

    Example:
      >>> def sig1():
      ...     return 'spam'
      >>> @copies(sig1)
      ... def sig2():
      ...     return sig1()
      >>> sig1() == sig2()
      True
      >>> sig1 is sig2
      False
      >>> sig1.__name__ == sig2.__name__
      False
      >>> sig1.__code__ is sig2.__code__
      True
    """

    if replaced is MISSING:
        return partial(copies, original)

    # We cannot copy built-in functions (at least on CPython; on PyPy, however,
    # this is possible, but it makes less sense there), so we ignore anything
    # that is not a user-defined function. We also skip the function on type
    # checking to speed up initialization and prevent possible type errors.
    if isinstance(original, FunctionType) and not TYPE_CHECKING:
        if hasattr(original, "clone"):  # Nuitka
            copy = original.clone()
        else:
            copy = FunctionType(
                original.__code__,
                original.__globals__,
                original.__name__,
                original.__defaults__,
                original.__closure__,
            )
            # python/cpython#112640
            copy.__kwdefaults__ = original.__kwdefaults__

        return update_wrapper(copy, replaced)

    return replaced
