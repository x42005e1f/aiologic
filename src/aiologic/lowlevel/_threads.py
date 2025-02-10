#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import weakref

from collections import deque
from functools import wraps

from wrapt import when_imported

from ._markers import MISSING
from ._thread import (
    allocate_lock,
    get_ident as current_thread_ident,
    start_new_thread as _start_new_thread,
)


def _get_python_thread(ident, /):
    global _get_python_thread

    from . import _monkey, _patcher

    threading = _monkey._import_python_original("threading")

    DummyThread = threading._DummyThread
    _active = threading._active

    _patcher.patch_threading()

    def _get_python_thread(ident, /):
        thread = _active.get(ident)

        if isinstance(thread, (DummyThread, threading._DummyThread)):
            thread = None

        return thread

    return _get_python_thread(ident)


def _get_eventlet_thread(ident, /):
    return None


@when_imported("eventlet.patcher")
def _get_eventlet_thread_hook(_):
    global _get_eventlet_thread

    def _get_eventlet_thread(ident, /):
        global _get_eventlet_thread

        from . import _monkey, _patcher

        threading = _monkey._import_eventlet_original("threading")

        DummyThread = threading._DummyThread
        _active = threading._active

        _patcher.patch_threading()

        def _get_eventlet_thread(ident, /):
            thread = _active.get(ident)

            if isinstance(thread, DummyThread):
                thread = None

            return thread

        return _get_eventlet_thread(ident)


def get_thread(ident, /):
    thread = _get_eventlet_thread(ident)

    if thread is None:
        thread = _get_python_thread(ident)

    return thread


def current_thread():
    thread = _get_eventlet_thread(current_thread_ident())

    if thread is None:
        thread = _get_python_thread(current_thread_ident())

    return thread


def once(func, /):
    lock = allocate_lock()
    result = MISSING

    @wraps(func)
    def wrapper():
        nonlocal result

        if result is MISSING:
            with lock:
                if result is MISSING:
                    result = func()

        return result

    return wrapper


_threads = set()

_finalizers = {}
_finalizers_lock = allocate_lock()

_shutdown_locks = deque()

try:
    from _thread import _local as ThreadLocal
except ImportError:
    object___new__ = object.__new__
    object___dir__ = object.__dir__
    object___getattribute__ = object.__getattribute__
    object___setattr__ = object.__setattr__
    object___delattr__ = object.__delattr__

    def get_thread_namespace(self, /, *, init=False):
        namespaces = object___getattribute__(self, "_namespaces_")

        if (ident := current_thread_ident()) in _threads:
            if ident in namespaces:
                namespace = namespaces[ident]
            elif init:

                def thread_deleted():
                    del namespaces[ident]

                add_thread_finalizer(ident, thread_deleted, ref=self)

                namespace = namespaces[ident] = object___getattribute__(
                    self, "_kwargs_"
                ).copy()
            else:
                namespace = None
        elif (thread := current_thread()) is not None:
            thread_ref = weakref.ref(thread)

            if thread_ref in namespaces:
                namespace = namespaces[thread_ref]
            elif init:
                try:
                    references = thread._localimpl_references
                except AttributeError:
                    thread._localimpl_references = references = set()

                def self_deleted(ref, /):
                    if (thread := thread_ref()) is not None:
                        thread._localimpl_references.remove(ref)

                def thread_deleted(ref, /):
                    if (self := self_ref()) is not None:
                        del object___getattribute__(
                            self,
                            "_namespaces_",
                        )[ref]

                self_ref = weakref.ref(self, self_deleted)
                thread_ref = weakref.ref(thread, thread_deleted)

                references.add(self_ref)

                namespace = namespaces[thread_ref] = object___getattribute__(
                    self, "_kwargs_"
                ).copy()
            else:
                namespace = None
        elif not init:
            namespace = None
        else:
            msg = "no current thread"
            raise RuntimeError(msg)

        return namespace

    class ThreadLocal:
        __slots__ = (
            "__weakref__",
            "_kwargs_",
            "_namespaces_",
        )

        def __new__(cls, /, **kwargs):
            self = object___new__(cls)

            object___setattr__(self, "_namespaces_", {})
            object___setattr__(self, "_kwargs_", kwargs)

            return self

        def __getnewargs_ex__(self, /):
            return ((), object___getattribute__(self, "_kwargs_"))

        def __repr__(self, /):
            namespace = get_thread_namespace(self, init=False)

            if namespace is not None:
                kwargs = namespace
            else:
                kwargs = object___getattribute__(self, "_kwargs_")

            items = (f"{key}={value!r}" for key, value in kwargs.items())

            return f"{self.__class__.__name__}({', '.join(items)})"

        def __dir__(self, /):
            names = object___dir__(self)

            if "__dict__" not in names:
                names.append("__dict__")

            return names

        def __getattribute__(self, /, name):
            if name == "__dict__":
                value = get_thread_namespace(self, init=True)
            elif name.startswith("_") and name.endswith("_"):
                value = object___getattribute__(self, name)
            else:
                namespace = get_thread_namespace(self, init=False)

                if namespace is None:
                    namespace = object___getattribute__(self, "_kwargs_")

                try:
                    value = namespace[name]
                except KeyError:
                    success = False
                else:
                    success = True

                if not success:
                    value = object___getattribute__(self, name)

            return value

        def __setattr__(self, /, name, value):
            if name == "__dict__":
                msg = "readonly attribute"
                raise AttributeError(msg)

            if name.startswith("_") and name.endswith("_"):
                object___setattr__(self, name, value)
            else:
                get_thread_namespace(self, init=True)[name] = value

        def __delattr__(self, /, name):
            if name == "__dict__":
                msg = "readonly attribute"
                raise AttributeError(msg)

            if name.startswith("_") and name.endswith("_"):
                object___delattr__(self, name)
            else:
                try:
                    namespace = get_thread_namespace(self, init=False)

                    if namespace is None:
                        raise KeyError

                    del namespace[name]
                except KeyError:
                    msg = (
                        f"{self.__class__.__name__!r} object"
                        f" has no attribute {name!r}"
                    )
                    raise AttributeError(msg) from None


@once
def _get_logger():
    from logging import getLogger

    return getLogger(__name__)


@once
def _register_shutdown():
    import atexit

    @atexit.register
    def _():
        while _shutdown_locks:
            try:
                shutdown_lock = _shutdown_locks.popleft()
            except IndexError:
                pass
            else:
                shutdown_lock.acquire()


def _run_thread_finalizer(ident, thread, /):
    if thread is not None:
        thread.join()

    while True:
        with _finalizers_lock:
            if thread is not None:
                callbacks = list(_finalizers[thread].values())
                _finalizers[thread].clear()
            else:
                callbacks = list(_finalizers[ident].values())
                _finalizers[ident].clear()

            if not callbacks:
                if thread is not None:
                    del _finalizers[thread]
                else:
                    del _finalizers[ident]

                break

        for _, func in callbacks:
            try:
                func()
            except (SystemExit, KeyboardInterrupt):
                raise
            except BaseException:  # noqa: BLE001
                if thread is not None:
                    thread_repr = repr(thread)
                else:
                    thread_repr = f"<thread {ident!r}>"

                _get_logger().exception(
                    "exception calling callback for %s",
                    thread_repr,
                )


def _run_new_thread(target, start_lock, shutdown_lock, /, *args, **kwargs):
    if shutdown_lock is not None:
        _shutdown_locks.append(shutdown_lock)
        _register_shutdown()

    try:
        ident = current_thread_ident()
        _threads.add(ident)

        try:
            _finalizers[ident] = {}

            try:
                start_lock.release()
                target(*args, **kwargs)
            finally:
                _run_thread_finalizer(ident, None)
        finally:
            _threads.remove(ident)
    finally:
        if shutdown_lock is not None:
            try:
                _shutdown_locks.remove(shutdown_lock)
            except ValueError:
                pass

            shutdown_lock.release()


def start_new_thread(target, args=(), kwargs=MISSING, *, daemon=True):
    if not callable(target):
        msg = "'target' argument must be callable"
        raise TypeError(msg)

    start_lock = allocate_lock()
    start_lock.acquire()

    if not daemon:
        shutdown_lock = allocate_lock()
        shutdown_lock.acquire()
    else:
        shutdown_lock = None

    try:
        args = (target, start_lock, shutdown_lock, *args)
    except TypeError:
        msg = "'args' argument must be an iterable"
        raise TypeError(msg) from None

    if kwargs is not MISSING:
        if not isinstance(kwargs, dict):
            msg = "'kwargs' argument must be a dictionary"
            raise TypeError(msg)

        ident = _start_new_thread(_run_new_thread, args, kwargs)
    else:
        ident = _start_new_thread(_run_new_thread, args)

    start_lock.acquire()

    return ident


def add_thread_finalizer(ident, func, /, *, ref=None):
    with _finalizers_lock:
        try:
            if ident is not None:
                callbacks = _finalizers[ident]
            else:
                callbacks = _finalizers[current_thread_ident()]
        except KeyError:
            if ident is not None:
                thread = get_thread(ident)

                if thread is None:
                    msg = f"no running thread {ident!r}"
                    raise RuntimeError(msg) from None
            else:
                thread = current_thread()

                if thread is None:
                    msg = "no current thread"
                    raise RuntimeError(msg) from None

            start_new_thread(
                _run_thread_finalizer,
                [ident, thread],
                daemon=False,
            )

            _finalizers[thread] = callbacks = {}

        key = object()

        if ref is not None:

            def deleted(_, /):
                try:
                    del callbacks[key]
                except KeyError:
                    pass

            callbacks[key] = (weakref.ref(ref, deleted), func)
        else:
            callbacks[key] = (None, func)

        return key


def remove_thread_finalizer(ident, key, /):
    with _finalizers_lock:
        try:
            if ident is not None:
                callbacks = _finalizers[ident]
            else:
                callbacks = _finalizers[current_thread_ident()]
        except KeyError:
            success = False
        else:
            try:
                del callbacks[key]
            except KeyError:
                success = False
            else:
                success = True

    return success
