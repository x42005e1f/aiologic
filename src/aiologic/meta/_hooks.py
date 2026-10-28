#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys
import weakref

from typing import TYPE_CHECKING, overload

from wrapt import register_post_import_hook

from ._markers import DEFAULT, MISSING
from ._static import getabsname_static, getname_static, isinstance_static

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, MutableMapping
    from types import ModuleType
    from typing import Any, TypeVar

    from ._markers import MissingType

    _HookT = TypeVar("_HookT", bound=Callable[[ModuleType], Any])

_NAMESPACE_HOOKS_NAME = "_aiologic_post_import_hooks"


def _maybe_create_rlock_if_nogil():
    global _maybe_create_rlock_if_nogil

    if "aiologic.thread" in sys.modules:
        from aiologic import thread

        try:
            _maybe_create_rlock_if_nogil = thread.create_rlock_if_nogil
        except AttributeError:
            thread_spec = getattr(thread, "__spec__", None)

            if getattr(thread_spec, "_initializing", True):
                return None

            raise

        return _maybe_create_rlock_if_nogil()

    return None


class _WeakBoundHookImpl:
    __slots__ = (
        "callback",
        "namespace",
    )

    def __init__(self, callback, namespace, /):
        self.callback = callback
        self.namespace = namespace

    def weakref_callback(self, weakref_obj, /):
        del self.callback
        del self.namespace


class _WeakBoundHook:
    __slots__ = (
        "__impl",
        "__spec",
        "__spec_weakref",
    )

    def __init__(self, callback, namespace, /):
        self.__impl = impl = _WeakBoundHookImpl(callback, namespace)
        self.__spec = spec = namespace.get("__spec__")
        try:
            self.__spec_weakref = weakref.ref(spec, impl.weakref_callback)
        except TypeError:
            self.__spec_weakref = None
        else:
            self.__spec = None

    def __init_subclass__(cls, /, **kwargs):
        bcs = __class__  # an implicit closure reference
        bcs_name = getname_static(bcs)

        msg = f"type {bcs_name!r} is not an acceptable base type"
        raise TypeError(msg)

    def __reduce__(self, /):
        cls = type(self)
        cls_name = getname_static(cls)

        msg = f"cannot pickle {cls_name!r} object"
        raise TypeError(msg)

    def __deepcopy__(self, memo, /):
        cls = type(self)
        cls_name = getname_static(cls)

        msg = f"cannot deep copy {cls_name!r} object"
        raise TypeError(msg)

    def __copy__(self, /):
        cls = type(self)
        cls_name = getname_static(cls)

        msg = f"cannot copy {cls_name!r} object"
        raise TypeError(msg)

    def __repr__(self, /):
        cls = type(self)
        cls_absname = getabsname_static(cls)

        self_repr = f"{cls_absname} object"
        if self._is_alive:
            state = "alive"
        else:
            state = "dead"

        return f"<{self_repr} at {id(self):#x}: {state}>"

    def __call__(self, /, *args, **kwargs):
        try:
            impl = self.__impl
            spec = self.__spec
            spec_weakref = self.__spec_weakref

            del self.__impl
            del self.__spec
            del self.__spec_weakref
        except AttributeError:  # already executed (possibly in parallel)
            return

        if spec_weakref is not None:
            spec = spec_weakref()
            if spec is None:
                return

        if spec is impl.namespace.get("__spec__"):
            callback = impl.callback

            del impl
            del spec
            del spec_weakref

            callback(*args, **kwargs)

    @property
    def __wrapped__(self, /):  # ruff: ignore[bad-dunder-method-name]
        try:
            return self.__impl.callback
        except AttributeError:
            return None

    @property
    def _namespace(self, /):
        try:
            return self.__impl.namespace
        except AttributeError:
            return None

    @property
    def _is_alive(self, /):
        try:
            impl = self.__impl
            spec = self.__spec
            spec_weakref = self.__spec_weakref
        except AttributeError:
            return False

        if spec_weakref is not None:
            spec = spec_weakref()
            if spec is None:
                return False

        return spec is impl.namespace.get("__spec__")


class _CountdownHook:
    __slots__ = (
        "__callback",
        "__vector",
    )

    def __init__(self, callback, count, /):
        self.__callback = callback
        self.__vector = [None] * (count - 1)  # a signal-safe counter

    def __init_subclass__(cls, /, **kwargs):
        bcs = __class__  # an implicit closure reference
        bcs_name = getname_static(bcs)

        msg = f"type {bcs_name!r} is not an acceptable base type"
        raise TypeError(msg)

    def __reduce__(self, /):
        cls = type(self)
        cls_name = getname_static(cls)

        msg = f"cannot pickle {cls_name!r} object"
        raise TypeError(msg)

    def __deepcopy__(self, memo, /):
        cls = type(self)
        cls_name = getname_static(cls)

        msg = f"cannot deep copy {cls_name!r} object"
        raise TypeError(msg)

    def __copy__(self, /):
        cls = type(self)
        cls_name = getname_static(cls)

        msg = f"cannot copy {cls_name!r} object"
        raise TypeError(msg)

    def __repr__(self, /):
        cls = type(self)
        cls_absname = getabsname_static(cls)

        self_repr = f"{cls_absname} object"
        state = f"_value={self._value}"

        return f"<{self_repr} at {id(self):#x} [{state}]>"

    def __call__(self, /, *args, **kwargs):
        try:
            self.__vector.pop()
        except IndexError:  # the last (or, unexpectedly, a subsequent)
            pass
        else:
            return

        try:
            callback = self.__callback

            del self.__callback
        except AttributeError:  # already executed (possibly in parallel)
            msg = "this hook was called more times than expected"
            raise RuntimeError(msg) from None

        callback(*args, **kwargs)

    @property
    def __wrapped__(self, /):  # ruff: ignore[bad-dunder-method-name]
        try:
            return self.__callback
        except AttributeError:
            return None

    @property
    def _value(self, /):
        return len(self.__vector) + (0 if self.__wrapped__ is None else 1)


class _DynamicHookDictionary(dict):  # ruff: ignore[subclass-builtin]
    __slots__ = ("__weakref__",)


class _DynamicHookWrapper:
    __slots__ = (
        "__hook",
        "__hooks_key",
        "__hooks_weakref",
        "_is_called",
        "_lock_if_nogil",
    )

    def __init__(self, hooks, hooks_key, hook, /):
        self.__hook = hook
        self.__hooks_key = hooks_key
        self.__hooks_weakref = weakref.ref(hooks)
        self._is_called = False
        self._lock_if_nogil = _maybe_create_rlock_if_nogil()

    def __init_subclass__(cls, /, **kwargs):
        bcs = __class__  # an implicit closure reference
        bcs_name = getname_static(bcs)

        msg = f"type {bcs_name!r} is not an acceptable base type"
        raise TypeError(msg)

    def __reduce__(self, /):
        cls = type(self)
        cls_name = getname_static(cls)

        msg = f"cannot pickle {cls_name!r} object"
        raise TypeError(msg)

    def __deepcopy__(self, memo, /):
        cls = type(self)
        cls_name = getname_static(cls)

        msg = f"cannot deep copy {cls_name!r} object"
        raise TypeError(msg)

    def __copy__(self, /):
        cls = type(self)
        cls_name = getname_static(cls)

        msg = f"cannot copy {cls_name!r} object"
        raise TypeError(msg)

    def __repr__(self, /):
        cls = type(self)
        cls_absname = getabsname_static(cls)

        self_repr = f"{cls_absname} object"
        if self._is_called:
            state = "called"
        else:
            state = "pending"

        return f"<{self_repr} at {id(self):#x}: {state}>"

    def __call__(self, /, *args, **kwargs):
        if self._unregister():  # only once
            with self._lock_if_nogil:
                self._is_called = True
                try:
                    hook = self.__hook

                    del self.__hook
                except AttributeError:  # a race condition (with set)
                    return

            hook(*args, **kwargs)

    def _set_if_not_called(self, hook, /):
        if self._is_called:
            return False

        with self._lock_if_nogil:
            self.__hook = hook

            if self._is_called:
                try:
                    del self.__hook
                except AttributeError:  # a race condition (with set or call)
                    pass

                return False

        return True

    def _unregister(self, /):
        if self._is_called:
            return False

        try:
            hooks_key = self.__hooks_key
            hooks_weakref = self.__hooks_weakref

            del self.__hooks_key
            del self.__hooks_weakref
        except AttributeError:  # already executed (possibly in parallel)
            return False

        if (hooks := hooks_weakref()) is not None:
            hook = hooks.pop(hooks_key)
            assert hook is self

            return True

        return False

    @property
    def __wrapped__(self, /):  # ruff: ignore[bad-dunder-method-name]
        try:
            return self.__hook
        except AttributeError:
            return None


def _register_bound_hook(
    namespace,
    module_name,
    bound_hook,
    *,
    name=MISSING,
    conjunction=DEFAULT,
):
    if conjunction is DEFAULT:
        conjunction = frozenset({module_name})

    try:
        hooks = namespace[_NAMESPACE_HOOKS_NAME]
    except KeyError:
        hooks = namespace.setdefault(
            _NAMESPACE_HOOKS_NAME,
            _DynamicHookDictionary(),
        )

    if name is MISSING or module_name in sys.modules:
        register_post_import_hook(bound_hook, module_name)
        return

    key = (name, conjunction, module_name)

    try:
        dynamic_hook = hooks[key]
    except KeyError:
        dynamic_hook = _DynamicHookWrapper(hooks, key, bound_hook)

        if dynamic_hook._lock_if_nogil is None:  # during initialization
            register_post_import_hook(bound_hook, module_name)
            return

        if dynamic_hook is hooks.setdefault(key, dynamic_hook):  # only once
            register_post_import_hook(dynamic_hook, module_name)
            return

        dynamic_hook = hooks[key]  # a race condition

    if not dynamic_hook._set_if_not_called(bound_hook):
        register_post_import_hook(bound_hook, module_name)


@overload
def when_imported_for(
    namespace: MutableMapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    hook: MissingType = MISSING,
    /,
    *,
    name: str | MissingType = MISSING,
) -> Callable[[_HookT], _HookT]: ...
@overload
def when_imported_for(
    namespace: MutableMapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    hook: _HookT,
    /,
    *,
    name: str | MissingType = MISSING,
) -> _HookT: ...
def when_imported_for(
    namespace,
    module_name_or_info,
    hook=MISSING,
    /,
    *,
    name=MISSING,
):
    if hook is MISSING:
        impl = when_imported_for

        def decorator(hook: _HookT, /) -> _HookT:
            return impl(namespace, module_name_or_info, hook, name=name)

        return decorator

    if not callable(hook):
        msg = "the third argument must be callable"
        raise TypeError(msg)

    if name is not MISSING and not isinstance_static(name, str):
        msg = "the `name` must be a string"
        raise TypeError(msg)

    bound_hook = _WeakBoundHook(hook, namespace)

    if isinstance_static(module_name_or_info, str):
        _register_bound_hook(
            namespace,
            module_name_or_info,
            bound_hook,
            name=name,
        )
        return hook

    conjunctions = set()

    for module_name_or_names in module_name_or_info:
        if isinstance_static(module_name_or_names, str):
            conjunctions.add(frozenset({module_name_or_names}))
        else:
            module_names = set()

            for module_name in module_name_or_names:
                if isinstance_static(module_name, str):
                    module_names.add(module_name)
                    continue

                msg = "the second argument must yield only strings at depth 2"
                raise TypeError(msg)

            conjunctions.add(frozenset(module_names))

    for conjunction in conjunctions:
        if len(conjunction) >= 2:
            countdown_hook = _CountdownHook(bound_hook, len(conjunction))

            for module_name in conjunction:
                _register_bound_hook(
                    namespace,
                    module_name,
                    _WeakBoundHook(countdown_hook, namespace),
                    name=name,
                    conjunction=conjunction,
                )
        elif len(conjunction) == 1:
            _register_bound_hook(
                namespace,
                *conjunction,
                bound_hook,
                name=name,
                conjunction=conjunction,
            )

    return hook
