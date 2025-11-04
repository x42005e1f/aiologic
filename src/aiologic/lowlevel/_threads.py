#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

from threading import main_thread
from typing import TYPE_CHECKING

from wrapt import when_imported

from aiologic._monkey import import_original, patched
from aiologic.meta import replaces

from . import _greenlets

if TYPE_CHECKING:
    import sys

    from threading import Thread
    from typing import Any

    from ._greenlets import _GreenletLike

    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self

try:
    _get_main_thread_ident = import_original(
        "_thread",
        "_get_main_thread_ident",
    )
except ImportError:

    def _is_main_thread() -> bool:
        return current_thread_ident() == main_thread().ident

    @when_imported("gevent.monkey")
    def _(_):
        @replaces(globals())
        def _is_main_thread():
            thread = main_thread()
            thread_ident = thread.ident
            thread_greenlet = getattr(thread, "_greenlet", None)

            if thread_greenlet is not None:
                thread_ident = getattr(thread, "_gevent_real_ident", None)

                if thread_ident is None:
                    answer = _greenlets._main_greenlet() is thread_greenlet

                    if answer:
                        thread._gevent_real_ident = current_thread_ident()

                    return answer

            return current_thread_ident() == thread_ident

else:

    def _is_main_thread() -> bool:
        return current_thread_ident() == _get_main_thread_ident()


def _current_python_thread() -> Thread | None:
    import threading

    _DummyThread = threading._DummyThread
    _active = threading._active

    @replaces(globals())
    def _current_python_thread():
        thread = _active.get(current_thread_ident())

        if isinstance(thread, _DummyThread):
            return None

        return thread

    @when_imported("gevent.monkey")
    @when_imported("eventlet.patcher")
    def _(_):
        @replaces(globals())
        def _current_python_thread():
            thread = _active.get(ident := current_thread_ident())

            if thread is None:
                return None

            if isinstance(thread, (_DummyThread, threading._DummyThread)):
                return None

            if patched("threading"):
                greenlet = _greenlets._current_greenlet()

                if id(greenlet) == ident and greenlet.parent is not None:
                    return None

            return thread

    return _current_python_thread()


def _current_eventlet_thread() -> Thread | None:
    return None


@when_imported("eventlet.patcher")
def _(_):
    @replaces(globals())
    def _current_eventlet_thread():
        from eventlet.patcher import original

        threading = original("threading")

        _DummyThread = threading._DummyThread
        _active = threading._active

        @replaces(globals())
        def _current_eventlet_thread():
            thread = _active.get(current_thread_ident())

            if isinstance(thread, _DummyThread):
                return None

            return thread

        return _current_eventlet_thread()


def _current_thread_or_main_greenlet() -> Thread | _GreenletLike:
    thread_or_greenlet = _current_python_thread()

    if thread_or_greenlet is None:
        thread_or_greenlet = _current_eventlet_thread()

        if thread_or_greenlet is None:
            if _is_main_thread():
                return main_thread()

            thread_or_greenlet = _greenlets._main_greenlet_if_exists()

            if thread_or_greenlet is None:
                msg = "no current thread or main greenlet"
                raise RuntimeError(msg)

    return thread_or_greenlet


def current_thread() -> Thread:
    thread = _current_python_thread()

    if thread is None:
        thread = _current_eventlet_thread()

        if thread is None:
            if _is_main_thread():
                return main_thread()

            msg = "no current thread"
            raise RuntimeError(msg)

    return thread


current_thread_ident = import_original("_thread", "get_ident")

try:
    _local = import_original("_thread", "_local")
except ImportError:
    import weakref

    object___new__ = object.__new__
    object___dir__ = object.__dir__
    object___getattribute__ = object.__getattribute__
    object___setattr__ = object.__setattr__
    object___delattr__ = object.__delattr__

    def _get_thread_namespace_noinit(instance: _local, /) -> dict[str, Any]:
        namespaces = object___getattribute__(instance, "_namespaces_")

        obj = _current_thread_or_main_greenlet()

        return namespaces.get(weakref.ref(obj))

    def _get_thread_namespace(instance: _local, /) -> dict[str, Any]:
        namespaces = object___getattribute__(instance, "_namespaces_")

        obj = _current_thread_or_main_greenlet()

        try:
            return namespaces[weakref.ref(obj)]
        except KeyError:
            pass

        try:
            references = obj._localimpl_references
        except AttributeError:
            obj._localimpl_references = references = set()

        def instance_deleted(ref, /):
            if (obj := obj_ref()) is not None:
                obj._localimpl_references.remove(ref)

        def obj_deleted(ref, /):
            if (instance := instance_ref()) is not None:
                del object___getattribute__(instance, "_namespaces_")[ref]

        instance_ref = weakref.ref(instance, instance_deleted)
        obj_ref = weakref.ref(obj, obj_deleted)

        references.add(instance_ref)

        namespace = namespaces[obj_ref] = {}

        return namespace

    class _local:
        __slots__ = (
            "__weakref__",
            "_namespaces_",
        )

        def __new__(cls, /) -> Self:
            self = object___new__(cls)

            object___setattr__(self, "_namespaces_", {})

            return self

        def __getstate__(self, /) -> None:
            return None

        def __dir__(self, /) -> list[str]:
            names = list(object___dir__(self))

            if "__dict__" not in names:
                names.append("__dict__")

            return names

        def __getattribute__(self, /, name: str) -> Any:
            if name == "__dict__":
                return _get_thread_namespace(self)

            if name.startswith("_") and name.endswith("_"):
                return object___getattribute__(self, name)

            if (namespace := _get_thread_namespace_noinit(self)) is not None:
                try:
                    return namespace[name]
                except KeyError:
                    pass

            return object___getattribute__(self, name)

        def __setattr__(self, /, name: str, value: object) -> None:
            if name == "__dict__":
                msg = "readonly attribute"
                raise AttributeError(msg)

            if name.startswith("_") and name.endswith("_"):
                object___setattr__(self, name, value)
                return

            _get_thread_namespace(self)[name] = value

        def __delattr__(self, /, name: str) -> None:
            if name == "__dict__":
                msg = "readonly attribute"
                raise AttributeError(msg)

            if name.startswith("_") and name.endswith("_"):
                object___delattr__(self, name)
                return

            if (namespace := _get_thread_namespace_noinit(self)) is not None:
                try:
                    del namespace[name]
                except KeyError:
                    pass
                else:
                    return

            object___delattr__(self, name)
