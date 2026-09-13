#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys
import weakref

from functools import update_wrapper
from types import FunctionType
from typing import TYPE_CHECKING

from wrapt import register_post_import_hook

from ._markers import MISSING
from ._static import isinstance_static

if TYPE_CHECKING:
    from types import ModuleType
    from typing import Any, TypeVar

    from ._markers import MissingType

    if sys.version_info >= (3, 9):
        from collections.abc import Callable, MutableMapping
    else:
        from typing import Callable, MutableMapping

    if sys.version_info >= (3, 10):
        from typing import ParamSpec
    else:
        from typing_extensions import ParamSpec

    if sys.version_info >= (3, 12):
        from typing import Protocol
    else:
        from typing_extensions import Protocol

if sys.version_info >= (3, 11):
    from typing import overload
else:
    from typing_extensions import overload

if TYPE_CHECKING:
    _T = TypeVar("_T")
    _T_co = TypeVar("_T_co", covariant=True)
    _HookT = TypeVar("_HookT", bound=Callable[[ModuleType], Any])
    _NamedCallableT = TypeVar(
        "_NamedCallableT",
        bound="_NamedCallable[..., Any]",
    )
    _P = ParamSpec("_P")

    class _NamedCallable(Protocol[_P, _T_co]):
        def __call__(
            self,
            /,
            *args: _P.args,
            **kwargs: _P.kwargs,
        ) -> _T_co: ...
        @property
        def __name__(  # ruff: ignore[bad-dunder-method-name]
            self,
            /,
        ) -> str: ...


_ANNOTATIONS_EAGER = sys.version_info < (3, 14)

if "_sentinel" not in globals():
    _sentinel = object()


class _BoundHookImpl:
    __slots__ = (
        "hook",
        "namespace",
    )

    def __init__(self, hook, namespace, /):
        self.hook = hook
        self.namespace = namespace

    def __call__(self, /, *args, **kwargs):
        try:
            hook = self.hook

            del self.hook
            del self.namespace
        except AttributeError:
            return

        try:
            hook(*args, **kwargs)
        finally:
            del hook
            del args
            del kwargs

    def weakref_callback(self, _, /):
        try:
            del self.hook
            del self.namespace
        except AttributeError:
            return


class _BoundHook:
    __slots__ = (
        "__impl",
        "__spec",
        "__spec_weakref",
    )

    def __init__(self, hook, namespace, /):
        self.__impl = impl = _BoundHookImpl(hook, namespace)
        self.__spec = spec = namespace.get("__spec__")
        try:
            self.__spec_weakref = weakref.ref(spec, impl.weakref_callback)
        except TypeError:
            self.__spec_weakref = None
        else:
            self.__spec = None

    def __init_subclass__(cls, /, **kwargs):
        bcs = __class__
        bcs_name = bcs.__name__

        msg = f"type {bcs_name!r} is not an acceptable base type"
        raise TypeError(msg)

    def __reduce__(self, /):
        cls = type(self)
        cls_name = cls.__name__

        msg = f"cannot pickle {cls_name!r} object"
        raise TypeError(msg)

    def __deepcopy__(self, memo, /):
        cls = type(self)
        cls_name = cls.__name__

        msg = f"cannot deep copy {cls_name!r} object"
        raise TypeError(msg)

    def __copy__(self, /):
        cls = type(self)
        cls_name = cls.__name__

        msg = f"cannot copy {cls_name!r} object"
        raise TypeError(msg)

    def __call__(self, /, *args, **kwargs):
        try:
            impl = self.__impl
            spec = self.__spec
            spec_weakref = self.__spec_weakref

            del self.__impl
            del self.__spec
            del self.__spec_weakref
        except AttributeError:
            return

        if spec_weakref is not None:
            spec = spec_weakref()
            if spec is None:
                return

        if spec is impl.namespace.get("__spec__"):
            try:
                impl.hook(*args, **kwargs)
            finally:
                del spec_weakref
                del spec
                del impl
                del args
                del kwargs


class _HookWrapper:
    __slots__ = (
        "_hook",
        "_is_not_called",
        "_lock_if_nogil",
    )

    def __init__(self, hook, lock, /):
        self._hook = hook
        self._is_not_called = True
        self._lock_if_nogil = lock

    def __init_subclass__(cls, /, **kwargs):
        bcs = __class__
        bcs_name = bcs.__name__

        msg = f"type {bcs_name!r} is not an acceptable base type"
        raise TypeError(msg)

    def __reduce__(self, /):
        cls = type(self)
        cls_name = cls.__name__

        msg = f"cannot pickle {cls_name!r} object"
        raise TypeError(msg)

    def __deepcopy__(self, memo, /):
        cls = type(self)
        cls_name = cls.__name__

        msg = f"cannot deep copy {cls_name!r} object"
        raise TypeError(msg)

    def __copy__(self, /):
        cls = type(self)
        cls_name = cls.__name__

        msg = f"cannot copy {cls_name!r} object"
        raise TypeError(msg)

    def __call__(self, /, *args, **kwargs):
        with self._lock_if_nogil:
            try:
                del self._is_not_called

                hook = self._hook

                del self._hook
            except AttributeError:
                return

        try:
            hook(*args, **kwargs)
        finally:
            del hook
            del args
            del kwargs


def _maybe_create_rlock_if_nogil():
    try:
        from aiologic.thread import create_rlock_if_nogil
    except ImportError:
        return None

    @replaces_with_outcome(globals())
    def _maybe_create_rlock_if_nogil():
        return create_rlock_if_nogil

    return _maybe_create_rlock_if_nogil()


@overload
def when_imported_for(
    namespace: MutableMapping[str, Any],
    module_name: str,
    hook: MissingType = MISSING,
    /,
    *,
    name: str | MissingType = MISSING,
) -> Callable[[_HookT], _HookT]: ...
@overload
def when_imported_for(
    namespace: MutableMapping[str, Any],
    module_name: str,
    hook: _HookT,
    /,
    *,
    name: str | MissingType = MISSING,
) -> _HookT: ...
def when_imported_for(
    namespace,
    module_name,
    hook=MISSING,
    /,
    *,
    name=MISSING,
):
    if hook is MISSING:
        impl = when_imported_for

        def decorator(hook: _HookT, /) -> _HookT:
            return impl(namespace, module_name, hook, name=name)

        return decorator

    bound_hook = _BoundHook(hook, namespace)

    if name is MISSING:
        register_post_import_hook(bound_hook, module_name)
        return hook

    try:
        hooks = namespace["_aiologic_import_hooks"]
    except KeyError:
        hooks = namespace.setdefault("_aiologic_import_hooks", {})

    try:
        hook_wrapper = hooks[name]
    except KeyError:
        lock = _maybe_create_rlock_if_nogil()

        if lock is None:
            register_post_import_hook(bound_hook, module_name)
            return hook

        hook_wrapper = _HookWrapper(bound_hook, lock)

        if hook_wrapper is hooks.setdefault(name, hook_wrapper):
            register_post_import_hook(hook_wrapper, module_name)
            return hook

        hook_wrapper = hooks[name]

    with hook_wrapper._lock_if_nogil:
        hook_wrapper._hook = bound_hook

        if not getattr(hook_wrapper, "_is_not_called", False):
            register_post_import_hook(bound_hook, module_name)

    return hook


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
    if replacer is MISSING:
        impl = replaces

        def decorator(replacer: _NamedCallableT, /) -> _NamedCallableT:
            return impl(namespace, replacer)

        return decorator

    name = replacer.__name__

    try:
        replaced = namespace[name]
    except KeyError:
        if "__spec__" in namespace:
            module_name = namespace.get("__name__")
        else:
            module_name = None

        if module_name is None:
            namespace_repr = "`namespace`"
        else:
            namespace_repr = f"module {module_name!r}"

        msg = f"{namespace_repr} has no function {name!r}"
        raise LookupError(msg) from None

    update_wrapper(replacer, replaced)

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
    if replacer is MISSING:
        impl = replaces_when_imported

        def decorator(replacer: _NamedCallableT, /) -> _NamedCallableT:
            return impl(namespace, module_name, replacer)

        return decorator

    name = replacer.__name__

    try:
        replaced = namespace[name]
    except KeyError:
        if "__spec__" in namespace:
            module_name = namespace.get("__name__")
        else:
            module_name = None

        if module_name is None:
            namespace_repr = "`namespace`"
        else:
            namespace_repr = f"module {module_name!r}"

        msg = f"{namespace_repr} has no function {name!r}"
        raise LookupError(msg) from None

    def hook(_):
        update_wrapper(replacer, replaced)

        try:
            del replacer.__wrapped__
        except AttributeError:
            pass

        namespace[name] = replacer

    when_imported_for(namespace, module_name, hook, name=name)

    return namespace[name]


@overload
def replaces_with_outcome(
    namespace: MutableMapping[str, Any],
    replacer_factory: MissingType = MISSING,
    /,
) -> Callable[[_NamedCallable[[], Callable[_P, _T]]], Callable[_P, _T]]: ...
@overload
def replaces_with_outcome(
    namespace: MutableMapping[str, Any],
    replacer_factory: _NamedCallable[[], Callable[_P, _T]],
    /,
) -> Callable[_P, _T]: ...
def replaces_with_outcome(namespace, replacer_factory=MISSING, /):
    if replacer_factory is MISSING:
        impl = replaces_with_outcome

        def decorator(
            replacer_factory: _NamedCallable[[], Callable[_P, _T]],
            /,
        ) -> Callable[_P, _T]:
            return impl(namespace, replacer_factory)

        return decorator

    name = replacer_factory.__name__

    spec = namespace.get("__spec__")

    replacer = _sentinel

    def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _T:
        nonlocal replacer

        if replacer is _sentinel:
            replacer = replacer_factory()

            if namespace.get("__spec__") is spec:
                namespace[name] = replacer

        return replacer(*args, **kwargs)

    for attr_name in ["__module__", "__name__", "__qualname__", "__doc__"]:
        try:
            attr_value = getattr(replacer_factory, attr_name)
        except AttributeError:
            pass
        else:
            setattr(wrapper, attr_name, attr_value)

    return wrapper


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
    if replaced is MISSING:
        impl = copies

        def decorator(replaced: Callable[_P, _T], /) -> Callable[_P, _T]:
            return impl(original, replaced)

        return decorator

    if TYPE_CHECKING:
        if replaced is not original:
            return replaced

    if not isinstance_static(original, FunctionType):
        if replaced is not original:
            return replaced

        msg = "cannot copy non-user-defined/compiled functions"
        raise TypeError(msg)

    if hasattr(original, "clone"):
        copy = original.clone()
    else:
        copy = original.__class__(
            code=original.__code__,
            closure=original.__closure__,
            globals=original.__globals__,
            name=original.__name__,
        )
        copy.__defaults__ = original.__defaults__
        copy.__kwdefaults__ = original.__kwdefaults__

    update_wrapper(copy, replaced)

    if copy.__kwdefaults__ is not None:
        copy.__kwdefaults__ = copy.__kwdefaults__.copy()

    if _ANNOTATIONS_EAGER:
        copy.__annotations__ = copy.__annotations__.copy()

    try:
        wrapped = replaced.__wrapped__
    except AttributeError:
        del copy.__wrapped__
    else:
        copy.__wrapped__ = wrapped

    return copy
