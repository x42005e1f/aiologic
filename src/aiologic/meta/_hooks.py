#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import weakref

from collections import namedtuple
from typing import TYPE_CHECKING, overload

from wrapt import register_post_import_hook, when_imported

from ._markers import MISSING
from ._static import getabsname_static, getname_static, isinstance_static

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping, MutableMapping
    from types import ModuleType
    from typing import Any, Literal, TypeVar

    from ._markers import MissingType

    _HookT = TypeVar("_HookT", bound=Callable[[ModuleType], Any])
    _UHookT = TypeVar("_UHookT", bound=Callable[[ModuleType | None], Any])

_NAMESPACE_HOOKS_NAME = "_aiologic_post_import_hooks"


def _maybe_create_turnstile_if_nogil():
    return None


@when_imported("aiologic.thread")
def _(thread):
    global _maybe_create_turnstile_if_nogil

    thread_spec = getattr(thread, "__spec__", None)

    def _maybe_create_turnstile_if_nogil():
        global _maybe_create_turnstile_if_nogil

        # see GrahamDumpleton/wrapt#366
        if getattr(thread_spec, "_initializing", False):
            return None

        try:
            _maybe_create_turnstile_if_nogil = thread.create_turnstile_if_nogil
        except AttributeError:
            if getattr(thread_spec, "_initializing", True):
                return None

            raise

        return _maybe_create_turnstile_if_nogil()


class _LazyTurnstileType:
    __slots__ = (
        "__impl",
        "__impl_holder",
        "__weakref__",
    )

    def __init__(self, /):
        self.__impl_holder = {}

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

        return f"<{self_repr} at {id(self):#x}>"

    def wait(self, /, timeout=-1):
        try:
            impl = self.__impl
        except AttributeError:
            impl = _maybe_create_turnstile_if_nogil()

            if impl is None:
                return True

            self.__impl = impl = self.__impl_holder.setdefault(None, impl)

        return impl.wait(timeout)


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
        "_is_called",
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
        self._is_called = False

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
        elif self._is_dead:
            state = "dead"
        else:
            state = "pending"

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
            self._is_called = True

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

    @property
    def _is_dead(self, /):
        return not self._is_alive


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
        state = f"_value={self._value!r}"

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
    __slots__ = (
        "__weakref__",
        "_turnstile_if_nogil",
        "_underlying",
    )


class _DynamicHook:
    __slots__ = (
        "__hooks_underlying",
        "__hooks_weakref",
        "__key",
        "_is_called",
        "_turnstile_if_nogil",
    )

    def __init__(self, hooks, key, /):
        self.__hooks_underlying = hooks._underlying
        self.__hooks_weakref = weakref.ref(hooks)
        self.__key = key
        self._is_called = False
        self._turnstile_if_nogil = hooks._turnstile_if_nogil

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
        elif self._is_dead:
            state = "dead"
        else:
            state = "pending"

        return f"<{self_repr} at {id(self):#x}: {state}>"

    def __call__(self, /, *args, **kwargs):
        if self._unregister():  # only once
            self._is_called = True
            self._turnstile_if_nogil.wait()

            hook = self.__hooks_underlying[self.__key]
            hook(*args, **kwargs)

    def _unregister(self, /):
        try:
            hooks_weakref = self.__hooks_weakref

            del self.__hooks_weakref
        except AttributeError:  # already executed (possibly in parallel)
            return False

        # wrapt>=1.15.0 handles unloading of modules that have already been
        # imported (see GrahamDumpleton/wrapt#217) as if they had never been
        # imported. Although this is a somewhat unusual use case, we should
        # handle it as well, for which we have to remove the current dynamic
        # hook when it is fired (due to its one-time nature).
        if (hooks := hooks_weakref()) is not None:
            hook = hooks.pop(self.__key)
            assert hook is self

        return True

    @property
    def __wrapped__(self, /):  # ruff: ignore[bad-dunder-method-name]
        hook = self.__hooks_underlying[self.__key]

        self._turnstile_if_nogil.wait()
        if self._is_called:
            return None

        return hook

    @property
    def _is_alive(self, /):
        try:
            _ = self.__hooks_weakref
        except AttributeError:
            return False

        return True

    @property
    def _is_dead(self, /):
        return not self._is_alive


_HookKey = namedtuple("_HookKey", ["name", "conjunction", "module_name"])


def _build_conjunctions_from(namespace, module_name_or_info, /, *, empty_ok):
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

            if not module_names and not empty_ok:
                msg = "the second argument must not yield empty iterables"
                raise ValueError(msg)

            conjunctions.add(frozenset(module_names))

    return conjunctions


def _create_bound_hooks_for(namespace, conjunctions, bound_hook, /, *, name):
    bound_hooks = {}

    for conjunction in conjunctions:
        if len(conjunction) >= 2:
            countdown_hook = _CountdownHook(bound_hook, len(conjunction))

            for module_name in conjunction:
                key = _HookKey(name, conjunction, module_name)
                bound_hooks[key] = _WeakBoundHook(countdown_hook, namespace)
        elif len(conjunction) == 1:
            key = _HookKey(name, conjunction, *conjunction)
            bound_hooks[key] = bound_hook

    return bound_hooks


def _register_bound_hooks_for(namespace, bound_hooks, /, *, name):
    if name is None:
        for key, bound_hook in bound_hooks.items():
            register_post_import_hook(bound_hook, key.module_name)

        return

    try:
        hooks = namespace[_NAMESPACE_HOOKS_NAME]
    except KeyError:
        hooks = _DynamicHookDictionary()
        hooks._turnstile_if_nogil = _maybe_create_turnstile_if_nogil()
        if hooks._turnstile_if_nogil is None:  # during initialization
            hooks._turnstile_if_nogil = _LazyTurnstileType()
        hooks._underlying = {}
        hooks = namespace.setdefault(_NAMESPACE_HOOKS_NAME, hooks)

    hooks._underlying.update(bound_hooks)
    hooks._turnstile_if_nogil.wait()

    for key in bound_hooks:
        if key in hooks:
            continue

        dynamic_hook = _DynamicHook(hooks, key)

        if dynamic_hook is hooks.setdefault(key, dynamic_hook):
            register_post_import_hook(dynamic_hook, key.module_name)


@overload
def when_imported_for(
    namespace: MutableMapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    hook: _UHookT,
    /,
    *,
    name: str,
    empty_ok: Literal[True],
) -> _UHookT: ...
@overload
def when_imported_for(
    namespace: MutableMapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    hook: MissingType = MISSING,
    /,
    *,
    name: str,
    empty_ok: Literal[True],
) -> Callable[[_UHookT], _UHookT]: ...
@overload
def when_imported_for(
    namespace: Mapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    hook: _UHookT,
    /,
    *,
    name: None = None,
    empty_ok: Literal[True],
) -> _UHookT: ...
@overload
def when_imported_for(
    namespace: Mapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    hook: MissingType = MISSING,
    /,
    *,
    name: None = None,
    empty_ok: Literal[True],
) -> Callable[[_UHookT], _UHookT]: ...
@overload
def when_imported_for(
    namespace: MutableMapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    hook: _HookT,
    /,
    *,
    name: str,
    empty_ok: Literal[False] = False,
) -> _HookT: ...
@overload
def when_imported_for(
    namespace: MutableMapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    hook: MissingType = MISSING,
    /,
    *,
    name: str,
    empty_ok: Literal[False] = False,
) -> Callable[[_HookT], _HookT]: ...
@overload
def when_imported_for(
    namespace: Mapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    hook: _HookT,
    /,
    *,
    name: None = None,
    empty_ok: Literal[False] = False,
) -> _HookT: ...
@overload
def when_imported_for(
    namespace: Mapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    hook: MissingType = MISSING,
    /,
    *,
    name: None = None,
    empty_ok: Literal[False] = False,
) -> Callable[[_HookT], _HookT]: ...
def when_imported_for(
    namespace,
    module_name_or_info,
    hook=MISSING,
    /,
    *,
    name=None,
    empty_ok=False,
):
    if hook is MISSING:
        impl = when_imported_for

        def decorator(hook, /):
            if hook is MISSING:
                msg = "the last argument must not be `MISSING`"
                raise TypeError(msg)

            return impl(
                namespace,
                module_name_or_info,
                hook,
                name=name,
                empty_ok=empty_ok,
            )

        return decorator

    if not callable(hook):
        msg = "the third argument must be callable"
        raise TypeError(msg)

    if name is not None and not isinstance_static(name, str):
        msg = "the `name` must be a string"
        raise TypeError(msg)

    bound_hook = _WeakBoundHook(hook, namespace)

    if isinstance_static(module_name_or_info, str):
        module_name = module_name_or_info

        if name is None:
            register_post_import_hook(bound_hook, module_name)
        else:
            key = _HookKey(name, frozenset({module_name}), module_name)
            _register_bound_hooks_for(namespace, {key: bound_hook}, name=name)

        return hook

    conjunctions = _build_conjunctions_from(
        namespace,
        module_name_or_info,
        empty_ok=empty_ok,
    )
    bound_hooks = _create_bound_hooks_for(
        namespace,
        conjunctions,
        bound_hook,
        name=name,
    )

    _register_bound_hooks_for(namespace, bound_hooks, name=name)

    if frozenset() in conjunctions:
        bound_hook(None)

    return hook
