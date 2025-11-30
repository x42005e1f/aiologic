#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from functools import partial, update_wrapper
from inspect import isfunction
from types import FunctionType
from typing import TYPE_CHECKING

from ._markers import MISSING

if TYPE_CHECKING:
    from typing import Any, Protocol, TypeVar, type_check_only

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

    @type_check_only
    class _NamedCallable(Protocol):
        # see the "callback protocols" section in PEP 544
        def __call__(self, /, *args: Any, **kwargs: Any) -> Any: ...
        @property
        def __name__(self, /) -> str: ...  # noqa: PLW3201

    _NamedCallableT = TypeVar("_NamedCallableT", bound=_NamedCallable)


@overload
def replaces(
    namespace: MutableMapping[str, object],
    replacer: MissingType = MISSING,
    /,
) -> Callable[[_NamedCallableT], _NamedCallableT]: ...
@overload
def replaces(
    namespace: MutableMapping[str, object],
    replacer: _NamedCallableT,
    /,
) -> _NamedCallableT: ...
def replaces(namespace, replacer=MISSING, /):
    """
    Wrap and replace the function of the same name in *namespace*.

    Unlike :func:`functools.wraps`, excludes the ``__wrapped__`` attribute to
    avoid memory leaks in a multithreaded environment.

    Used for global rebinding.

    Raises:
      LookupError:
        if there is no function of the same name in *namespace*.

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

    # The `KeyError` when the retrieval fails is not informative enough, so it
    # is replaced with a `LookupError` with a more informative error message.
    try:
        wrapped = namespace[name]
    except KeyError:
        if "__spec__" in namespace:  # a module namespace
            namespace_repr = f"module {namespace['__name__']!r}"
        else:
            namespace_repr = "`namespace`"

        msg = f"{namespace_repr} has no function {name!r}"
        raise LookupError(msg) from None
    else:
        update_wrapper(replacer, wrapped)

    # Usually, the decorator is called for a newly defined function, but it can
    # also be used in parallel for older ones, so we have to handle concurrent
    # attempts to delete the attribute.
    try:
        del replacer.__wrapped__
    except AttributeError:
        pass

    namespace[name] = replacer

    return replacer


# Until python/typing#548 is resolved, we can only go one of two ways (not
# both):
# * require the parameter lists of both functions to match (via `ParamSpec`)
# * support callable subtypes, such as user-defined protocols (via `TypeVar`)
# Here, we choose the first way to prevent obvious type errors when applying
# the decorator to regular functions. This is not very suitable for forced
# copying, as it will require the user to use `cast()` to preserve the original
# type, but for lack of a better option...
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

    If *original* and *replaced* are the same function, it forces copying
    (``copies(func, func)`` is always a new copy of ``func``). Otherwise, does
    nothing on type checking to prevent type errors.

    Used to optimize functions which delegate all the work to others.

    Raises:
      TypeError:
        if copying is forced and *original* is not a user-defined function.

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

    # We skip the function on type checking to speed up initialization and
    # prevent possible type errors.
    if TYPE_CHECKING:
        if replaced is not original:
            return replaced

    # We also cannot copy built-in functions (at least on CPython; on PyPy,
    # however, this is possible, but it makes less sense there), so we ignore
    # anything that is not a user-defined function.
    if not isfunction(original):
        if replaced is not original:
            return replaced

        msg = "cannot copy non-user-defined functions"
        raise TypeError(msg)

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
