#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys
import weakref

from collections import namedtuple
from typing import TYPE_CHECKING, overload

from wrapt import register_post_import_hook, when_imported

from ._markers import DEFAULT, MISSING
from ._names import resolve_name, resolve_name_with_parents
from ._static import getabsname_static, getname_static, isinstance_static

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping, MutableMapping
    from types import ModuleType
    from typing import Any, Literal, TypeVar

    from ._markers import DefaultType, MissingType

    _HookT = TypeVar("_HookT", bound=Callable[[ModuleType], Any])
    _UHookT = TypeVar("_UHookT", bound=Callable[[ModuleType | None], Any])


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
        "__bound_hook",
        "__value_vector",
        "_conjunction",
        "_name",
        "_namespace",
    )

    def __init__(self, bound_hook, conjunction, /, *, namespace, name):
        self.__bound_hook = bound_hook
        self.__value_vector = [None] * (len(conjunction) - 1)
        self._conjunction = conjunction
        self._name = name
        self._namespace = namespace

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
            self.__value_vector.pop()
        except IndexError:  # the last (or, unexpectedly, a subsequent)
            pass
        else:
            return

        try:
            bound_hook = self.__bound_hook

            del self.__bound_hook
        except AttributeError:  # already executed (possibly in parallel)
            msg = "this hook was called more times than expected"
            raise RuntimeError(msg) from None

        for module_name in self._conjunction:
            if module_name not in sys.modules:
                _create_and_register_bound_hooks_for(
                    self._namespace,
                    {self._conjunction},
                    bound_hook,
                    name=self._name,
                )
                return

        bound_hook(*args, **kwargs)

    @property
    def __wrapped__(self, /):  # ruff: ignore[bad-dunder-method-name]
        try:
            return self.__bound_hook
        except AttributeError:
            return None

    @property
    def _initial_value(self, /):
        return len(self._conjunction)

    @property
    def _value(self, /):
        return len(self.__value_vector) + (
            0 if self.__wrapped__ is None else 1
        )


class _DynamicHookDictionary(dict):  # ruff: ignore[subclass-builtin]
    __slots__ = (
        "__weakref__",
        "_turnstile_if_nogil",
        "_underlying",
    )


class _DynamicHook:
    __slots__ = (
        "__dynamic_hooks_underlying",
        "__dynamic_hooks_weakref",
        "__key",
        "_is_called",
        "_turnstile_if_nogil",
    )

    def __init__(self, dynamic_hooks, key, /):
        self.__dynamic_hooks_underlying = dynamic_hooks._underlying
        self.__dynamic_hooks_weakref = weakref.ref(dynamic_hooks)
        self.__key = key
        self._is_called = False
        self._turnstile_if_nogil = dynamic_hooks._turnstile_if_nogil

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

            bound_hook = self.__dynamic_hooks_underlying[self.__key]
            bound_hook(*args, **kwargs)

    def _unregister(self, /):
        try:
            dynamic_hooks_weakref = self.__dynamic_hooks_weakref

            del self.__dynamic_hooks_weakref
        except AttributeError:  # already executed (possibly in parallel)
            return False

        # wrapt>=1.15.0 handles unloading of modules that have already been
        # imported (see GrahamDumpleton/wrapt#217) as if they had never been
        # imported. Although this is a somewhat unusual use case, we should
        # handle it as well, for which we have to remove the current dynamic
        # hook when it is fired (due to its one-time nature).
        if (dynamic_hooks := dynamic_hooks_weakref()) is not None:
            dynamic_hook = dynamic_hooks.pop(self.__key)
            assert dynamic_hook is self

        return True

    @property
    def __wrapped__(self, /):  # ruff: ignore[bad-dunder-method-name]
        bound_hook = self.__dynamic_hooks_underlying[self.__key]

        self._turnstile_if_nogil.wait()
        if self._is_called:
            return None

        return bound_hook

    @property
    def _is_alive(self, /):
        try:
            _ = self.__dynamic_hooks_weakref
        except AttributeError:
            return False

        return True

    @property
    def _is_dead(self, /):
        return not self._is_alive


_HookKey = namedtuple("_HookKey", ["name", "conjunction", "module_name"])


def _get_dynamic_hooks(namespace, /):
    try:
        hooks = namespace["_aiologic_post_import_hooks"]
    except KeyError:
        hooks = _DynamicHookDictionary()
        hooks._turnstile_if_nogil = _maybe_create_turnstile_if_nogil()
        if hooks._turnstile_if_nogil is None:  # during initialization
            hooks._turnstile_if_nogil = _LazyTurnstileType()
        hooks._underlying = {}
        hooks = namespace.setdefault("_aiologic_post_import_hooks", hooks)

    return hooks


def _build_conjunctions_from(
    namespace,
    module_name_or_info,
    /,
    *,
    empty_ok,
    parents,
    package,
):
    if isinstance_static(module_name_or_info, str):
        module_name = module_name_or_info
        if parents:
            resolved = resolve_name_with_parents(module_name, package)
        else:
            resolved = [resolve_name(module_name, package)]
        return {frozenset(resolved)}

    conjunctions = set()

    for module_name_or_names in module_name_or_info:
        if isinstance_static(module_name_or_names, str):
            module_name = module_name_or_names
            if parents:
                resolved = resolve_name_with_parents(module_name, package)
            else:
                resolved = [resolve_name(module_name, package)]
            conjunctions.add(frozenset(resolved))
            continue

        module_names = set()

        for module_name in module_name_or_names:
            if isinstance_static(module_name, str):
                if parents:
                    resolved = resolve_name_with_parents(module_name, package)
                else:
                    resolved = [resolve_name(module_name, package)]
                module_names.update(resolved)
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
            countdown_hook = _CountdownHook(
                bound_hook,
                conjunction,
                namespace=namespace,
                name=name,
            )

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

    dynamic_hooks = _get_dynamic_hooks(namespace)
    dynamic_hooks._underlying.update(bound_hooks)
    dynamic_hooks._turnstile_if_nogil.wait()

    for key in bound_hooks:
        if key not in dynamic_hooks:
            dynamic_hook = _DynamicHook(dynamic_hooks, key)

            if dynamic_hook is dynamic_hooks.setdefault(key, dynamic_hook):
                register_post_import_hook(dynamic_hook, key.module_name)


def _create_and_register_bound_hooks_for(
    namespace,
    conjunctions,
    bound_hook,
    /,
    *,
    name,
):
    _register_bound_hooks_for(
        namespace,
        _create_bound_hooks_for(
            namespace,
            conjunctions,
            bound_hook,
            name=name,
        ),
        name=name,
    )


@overload
def when_imported_for(
    namespace: MutableMapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    hook: _UHookT,
    /,
    *,
    empty_ok: Literal[True],
    parents: bool = False,
    package: str | None | DefaultType = DEFAULT,
    name: str,
) -> _UHookT: ...
@overload
def when_imported_for(
    namespace: MutableMapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    hook: MissingType = MISSING,
    /,
    *,
    empty_ok: Literal[True],
    parents: bool = False,
    package: str | None | DefaultType = DEFAULT,
    name: str,
) -> Callable[[_UHookT], _UHookT]: ...
@overload
def when_imported_for(
    namespace: Mapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    hook: _UHookT,
    /,
    *,
    empty_ok: Literal[True],
    parents: bool = False,
    package: str | None | DefaultType = DEFAULT,
    name: None = None,
) -> _UHookT: ...
@overload
def when_imported_for(
    namespace: Mapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    hook: MissingType = MISSING,
    /,
    *,
    empty_ok: Literal[True],
    parents: bool = False,
    package: str | None | DefaultType = DEFAULT,
    name: None = None,
) -> Callable[[_UHookT], _UHookT]: ...
@overload
def when_imported_for(
    namespace: MutableMapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    hook: _HookT,
    /,
    *,
    empty_ok: Literal[False] = False,
    parents: bool = False,
    package: str | None | DefaultType = DEFAULT,
    name: str,
) -> _HookT: ...
@overload
def when_imported_for(
    namespace: MutableMapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    hook: MissingType = MISSING,
    /,
    *,
    empty_ok: Literal[False] = False,
    parents: bool = False,
    package: str | None | DefaultType = DEFAULT,
    name: str,
) -> Callable[[_HookT], _HookT]: ...
@overload
def when_imported_for(
    namespace: Mapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    hook: _HookT,
    /,
    *,
    empty_ok: Literal[False] = False,
    parents: bool = False,
    package: str | None | DefaultType = DEFAULT,
    name: None = None,
) -> _HookT: ...
@overload
def when_imported_for(
    namespace: Mapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    hook: MissingType = MISSING,
    /,
    *,
    empty_ok: Literal[False] = False,
    parents: bool = False,
    package: str | None | DefaultType = DEFAULT,
    name: None = None,
) -> Callable[[_HookT], _HookT]: ...
def when_imported_for(
    namespace,
    module_name_or_info,
    hook=MISSING,
    /,
    *,
    empty_ok=False,
    parents=False,
    package=DEFAULT,
    name=None,
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
                empty_ok=empty_ok,
                parents=parents,
                package=package,
                name=name,
            )

        return decorator

    if not callable(hook):
        msg = "the third argument must be callable"
        raise TypeError(msg)

    if name is not None and not isinstance_static(name, str):
        msg = "the `name` must be a string"
        raise TypeError(msg)

    if package is DEFAULT:
        package = getattr(namespace.get("__spec__"), "name", None)

    bound_hook = _WeakBoundHook(hook, namespace)
    conjunctions = _build_conjunctions_from(
        namespace,
        module_name_or_info,
        empty_ok=empty_ok,
        parents=parents,
        package=package,
    )

    _create_and_register_bound_hooks_for(
        namespace,
        conjunctions,
        bound_hook,
        name=name,
    )

    if frozenset() in conjunctions:
        bound_hook(None)

    return hook
