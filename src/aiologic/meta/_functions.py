#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys
import weakref

from functools import update_wrapper
from types import FunctionType
from typing import TYPE_CHECKING

from wrapt import (
    register_post_import_hook,  # wrapt>=1.16.0: transparent
)

from ._markers import MISSING
from ._static import isinstance_static

if TYPE_CHECKING:
    from typing import Any, TypeVar

    from ._markers import MissingType

    if sys.version_info >= (3, 9):  # PEP 585
        from collections.abc import Callable, MutableMapping
    else:
        from typing import Callable, MutableMapping

    if sys.version_info >= (3, 10):  # PEP 612
        from typing import ParamSpec
    else:  # typing-extensions>=3.10.0
        from typing_extensions import ParamSpec

    if sys.version_info >= (3, 12):  # various bug fixes and improvements
        from typing import Protocol
    else:  # typing-extensions>=4.10.0
        from typing_extensions import Protocol

if sys.version_info >= (3, 11):  # python/cpython#31716: introspectable
    from typing import overload
else:  # typing-extensions>=4.2.0
    from typing_extensions import overload

if TYPE_CHECKING:
    _T = TypeVar("_T")
    _NamedCallableT = TypeVar("_NamedCallableT", bound="_NamedCallable")
    _P = ParamSpec("_P")

    class _NamedCallable(Protocol):
        def __call__(self, /, *args: Any, **kwargs: Any) -> Any: ...
        @property
        def __name__(self, /) -> str: ...  # noqa: PLW3201


# before PEP 649
_ANNOTATIONS_EAGER = sys.version_info < (3, 14)


@overload
def replaces(
    namespace: MutableMapping[str, Any],
    replacer: MissingType = MISSING,
    /,
) -> Callable[[_NamedCallableT], _NamedCallableT]: ...
@overload
def replaces(
    namespace: MutableMapping[str, Any],
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

    # When the last parameter is not passed, we return a new decorator object
    # bound to the passed arguments (and to the function itself, so that it
    # always refers to the called function even after the module is reloaded).
    # The object is a separate function rather than an instance of
    # `functools.partial` to prevent the call from succeeding without a single
    # argument being passed.
    if replacer is MISSING:
        impl = replaces  # to avoid `__globals__`

        def decorator(replacer: _NamedCallableT, /) -> _NamedCallableT:
            """
            A partial application of :func:`replaces` to its first argument.
            """

            return impl(namespace, replacer)

        return decorator

    # The replaced function may have a different `__name__` attribute value
    # than the replacer, so we must always use the name obtained before
    # wrapping.
    name = replacer.__name__

    # The `KeyError` when the retrieval fails is not informative enough, so it
    # is replaced with a `LookupError` with a more informative error message.
    try:
        replaced = namespace[name]
    except KeyError:
        if "__spec__" in namespace:  # a module namespace
            module_name = namespace.get("__name__")
        else:
            module_name = None

        if module_name is None:
            namespace_repr = "`namespace`"
        else:
            namespace_repr = f"module {module_name!r}"

        msg = f"{namespace_repr} has no function {name!r}"
        raise LookupError(msg) from None

    # When `update_wrapper()` is applied sequentially (a special case of
    # parallel calls) on the same namespace to functions of the same name, they
    # will refer to each other via the `__wrapped__` attribute, which will
    # prevent them from being deleted from memory. Therefore, we delete the
    # attribute after the call to break the reference chain.
    update_wrapper(replacer, replaced)

    # Usually, the decorator is called for a newly defined function, but it can
    # also be used in parallel for older ones, so we have to handle concurrent
    # attempts to delete the attribute.
    try:
        del replacer.__wrapped__
    except AttributeError:
        pass

    namespace[name] = replacer

    return replacer


@overload
def replaces_when_imported(
    namespace: MutableMapping[str, Any],
    module_name: str,
    replacer: MissingType = MISSING,
    /,
) -> Callable[[_NamedCallableT], _NamedCallableT]: ...
@overload
def replaces_when_imported(
    namespace: MutableMapping[str, Any],
    module_name: str,
    replacer: _NamedCallableT,
    /,
) -> _NamedCallableT: ...
def replaces_when_imported(namespace, module_name, replacer=MISSING, /):
    """
    Wrap and replace the function of the same name in *namespace*, but only
    when the specified *module_name* is imported.

    It has the same effect as :func:`replaces` but is delayed: when called, it
    registers a post import hook bound to the replaced function, which fires
    when someone imports the target module, and only then does the effect
    actually take place. Additionally, if *namespace* is a module namespace,
    the hook is deactivated when the module is reloaded (e.g., by
    :func:`importlib.reload`) to prevent incorrect replacements.

    Used to implement support for optional dependencies.

    Raises:
      LookupError:
        if there is no function of the same name in *namespace*.

    Example:
      >>> def in_asyncio_context():
      ...     return False
      >>> @replaces_when_imported(globals(), 'asyncio')
      ... def in_asyncio_context():
      ...     import asyncio
      ...     @replaces(globals())
      ...     def in_asyncio_context():
      ...         return asyncio._get_running_loop() is not None
      ...     return in_asyncio_context()
    """

    # When the last parameter is not passed, we return a new decorator object
    # bound to the passed arguments (and to the function itself, so that it
    # always refers to the called function even after the module is reloaded).
    # The object is a separate function rather than an instance of
    # `functools.partial` to prevent the call from succeeding without a single
    # argument being passed.
    if replacer is MISSING:
        impl = replaces_when_imported  # to avoid `__globals__`

        def decorator(replacer: _NamedCallableT, /) -> _NamedCallableT:
            """
            A partial application of :func:`replaces_when_imported` to its
            first arguments.
            """

            return impl(namespace, module_name, replacer)

        return decorator

    # The replaced function may have a different `__name__` attribute value
    # than the replacer, so we must always use the name obtained before
    # wrapping.
    name = replacer.__name__

    # The `KeyError` when the retrieval fails is not informative enough, so it
    # is replaced with a `LookupError` with a more informative error message.
    try:
        replaced = namespace[name]
    except KeyError:
        if "__spec__" in namespace:  # a module namespace
            module_name = namespace.get("__name__")
        else:
            module_name = None

        if module_name is None:
            namespace_repr = "`namespace`"
        else:
            namespace_repr = f"module {module_name!r}"

        msg = f"{namespace_repr} has no function {name!r}"
        raise LookupError(msg) from None

    # When the module is reloaded, the registered hook may become irrelevant.
    # At best, it may only affect performance (reload without changes), but at
    # worst, it may replace a new implementation with an outdated version
    # (reload with changes, for example via an IDE). But because
    # `module.__spec__` is replaced with a new object on every reload, we can
    # take advantage of this and bind the hook to the current object.
    spec = namespace.get("__spec__")

    # The hook should not have strong references to the objects it uses, except
    # for `namespace`, because otherwise they will remain alive after the
    # module is reloaded (and before the associated import), which could be
    # considered a memory leak. We solve this by referring to `module.__spec__`
    # weakly and removing references to the other objects via the callback
    # whenever possible.
    def weakref_callback(_):
        nonlocal replaced
        nonlocal replacer

        del replaced
        del replacer

    try:
        spec_ref = weakref.ref(spec, weakref_callback)
    except TypeError:  # not weakrefable
        spec_ref = None
    else:
        spec = None

    def hook(_):
        nonlocal spec

        if spec_ref is not None:
            spec = spec_ref()

            if spec is None:
                return

        if namespace.get("__spec__") is spec:
            # When `update_wrapper()` is applied sequentially (a special case
            # of parallel calls) on the same namespace to functions of the same
            # name, they will refer to each other via the `__wrapped__`
            # attribute, which will prevent them from being deleted from
            # memory. Therefore, we delete the attribute after the call to
            # break the reference chain.
            update_wrapper(replacer, replaced)

            # Usually, the decorator is called for a newly defined function,
            # but it can also be used in parallel for older ones, so we have to
            # handle concurrent attempts to delete the attribute.
            try:
                del replacer.__wrapped__
            except AttributeError:
                pass

            namespace[name] = replacer

    register_post_import_hook(hook, module_name)

    return namespace[name]


# Until python/typing#548 is resolved, we can only go one of two ways (not
# both):
# * require the parameter lists of both functions to match (via `ParamSpec`)
# * support callable subtypes, such as user-defined protocols (via `TypeVar`)
# Here, we choose the first way to prevent obvious type errors when applying
# the decorator to regular functions.
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
    Replace with a copy of *original* if that is a :ref:`user-defined function
    <user-defined-funcs>`, and make the copy look like *replaced* function.

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

    # When the last parameter is not passed, we return a new decorator object
    # bound to the passed arguments (and to the function itself, so that it
    # always refers to the called function even after the module is reloaded).
    # The object is a separate function rather than an instance of
    # `functools.partial` to prevent the call from succeeding without a single
    # argument being passed.
    if replaced is MISSING:
        impl = copies  # to avoid `__globals__`

        def decorator(replaced: Callable[_P, _T], /) -> Callable[_P, _T]:
            """
            A partial application of :func:`copies` to its first argument.
            """

            return impl(original, replaced)

        return decorator

    # We skip the function on type checking to speed up initialization and
    # prevent possible type errors (mismatches between expected and actual
    # annotations in Sphinx).
    if TYPE_CHECKING:
        if replaced is not original:
            return replaced

    # We cannot copy built-in functions (at least on CPython; on PyPy, however,
    # this is possible, but it makes less sense there), so we ignore anything
    # that is not a user-defined function.
    if not isinstance_static(original, FunctionType):
        if replaced is not original:
            return replaced

        msg = "cannot copy non-user-defined/compiled functions"
        raise TypeError(msg)

    # A well-known method of "deep" (actually not) copying of functions is to
    # create a new instance of the function type with the same parameters as
    # the original function. Here are some related links:
    # * https://stackoverflow.com/q/6527633
    # * https://stackoverflow.com/q/13503079
    # * https://github.com/Nuitka/Nuitka/commit/bdfad66
    # Note that functions compiled by Cython have a different type and
    # therefore will not reach the following code section.
    if hasattr(original, "clone"):  # Nuitka
        copy = original.clone()
    else:
        copy = original.__class__(
            code=original.__code__,
            closure=original.__closure__,
            globals=original.__globals__,
            name=original.__name__,
        )
        copy.__defaults__ = original.__defaults__
        copy.__kwdefaults__ = original.__kwdefaults__  # python/cpython#112640

    update_wrapper(copy, replaced)

    # Note, Nuitka≥2.0 already copies the following objects, but it is unknown
    # how the `functools.update_wrapper()` behavior might change in the context
    # of python/cpython#85403 and python/cpython#85404, so we copy them anyway.

    if copy.__kwdefaults__ is not None:
        copy.__kwdefaults__ = copy.__kwdefaults__.copy()

    if _ANNOTATIONS_EAGER:
        copy.__annotations__ = copy.__annotations__.copy()

    # to preserve the signature
    try:
        wrapped = replaced.__wrapped__
    except AttributeError:
        del copy.__wrapped__
    else:
        copy.__wrapped__ = wrapped

    return copy
