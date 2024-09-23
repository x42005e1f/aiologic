#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

__all__ = (
    "ThreadLocal",
    "start_new_thread",
    "add_thread_finalizer",
    "remove_thread_finalizer",
)

from sys import modules
from importlib import import_module

from . import patcher
from .markers import MISSING


def get_python_thread(ident, /):
    global get_python_thread

    try:
        threading = import_module("threading")

        if patcher.eventlet_patched("threading") or patcher.gevent_patched(
            "threading"
        ):
            raise ImportError

        _active = threading._active
    except (ImportError, AttributeError):

        def get_python_thread(ident, /):
            return None

    else:
        patcher.patch_threading()

        try:
            DummyThread = threading._DummyThread
        except AttributeError:

            def get_python_thread(ident, /):
                return _active.get(ident)

        else:

            def get_python_thread(ident, /):
                thread = _active.get(ident)

                if isinstance(thread, DummyThread):
                    thread = None

                return thread

    return get_python_thread(ident)


def get_eventlet_thread(ident, /):
    global get_eventlet_thread

    if "eventlet" in modules:
        try:
            threading = patcher.import_eventlet_original("threading")

            if threading is None:
                raise ImportError

            _active = threading._active
        except (ImportError, AttributeError):

            def get_eventlet_thread(ident, /):
                return None

        else:
            patcher.patch_threading()

            try:
                DummyThread = threading._DummyThread
            except AttributeError:

                def get_eventlet_thread(ident, /):
                    return _active.get(ident)

            else:

                def get_eventlet_thread(ident, /):
                    thread = _active.get(ident)

                    if isinstance(thread, DummyThread):
                        thread = None

                    return thread

        thread = get_eventlet_thread(ident)
    else:
        thread = None

    return thread


def get_thread(ident, /):
    thread = get_python_thread(ident)

    if thread is None:
        thread = get_eventlet_thread(ident)

    return thread


def current_python_thread():
    global current_python_thread

    try:
        threading = import_module("threading")

        if patcher.eventlet_patched("threading") or patcher.gevent_patched(
            "threading"
        ):
            raise ImportError

        _active = threading._active
    except ImportError:

        def current_python_thread():
            return None

    except AttributeError:
        try:
            current_thread = threading.current_thread
        except AttributeError:

            def current_python_thread():
                return None

        else:
            patcher.patch_threading()

            try:
                DummyThread = threading._DummyThread
            except AttributeError:
                current_python_thread = current_thread
            else:

                def current_python_thread():
                    thread = current_thread()

                    if isinstance(thread, DummyThread):
                        thread = None

                    return thread

    else:
        try:
            get_ident = threading.get_ident
        except AttributeError:

            def current_python_thread():
                return None

        else:
            patcher.patch_threading()

            try:
                DummyThread = threading._DummyThread
            except AttributeError:

                def current_python_thread():
                    return _active.get(get_ident())

            else:

                def current_python_thread():
                    thread = _active.get(get_ident())

                    if isinstance(thread, DummyThread):
                        thread = None

                    return thread

    return current_python_thread()


def current_eventlet_thread():
    global current_eventlet_thread

    if "eventlet" in modules:
        try:
            threading = patcher.import_eventlet_original("threading")

            if threading is None:
                raise ImportError

            _active = threading._active
        except ImportError:

            def current_eventlet_thread():
                return None

        except AttributeError:
            try:
                current_thread = threading.current_thread
            except AttributeError:

                def current_eventlet_thread():
                    return None

            else:
                patcher.patch_threading()

                try:
                    DummyThread = threading._DummyThread
                except AttributeError:
                    current_eventlet_thread = current_thread
                else:

                    def current_eventlet_thread():
                        thread = current_thread()

                        if isinstance(thread, DummyThread):
                            thread = None

                        return thread

        else:
            try:
                get_ident = threading.get_ident
            except AttributeError:

                def current_eventlet_thread():
                    return None

            else:
                patcher.patch_threading()

                try:
                    DummyThread = threading._DummyThread
                except AttributeError:

                    def current_eventlet_thread():
                        return _active.get(get_ident())

                else:

                    def current_eventlet_thread():
                        thread = _active.get(get_ident())

                        if isinstance(thread, DummyThread):
                            thread = None

                        return thread

        thread = current_eventlet_thread()
    else:
        thread = None

    return thread


def current_thread():
    thread = current_python_thread()

    if thread is None:
        thread = current_eventlet_thread()

    return thread


try:
    from .thread import allocate_lock, get_ident
except ImportError:
    from types import SimpleNamespace as ThreadLocal

    def start_new_thread(target, args=(), kwargs=MISSING, *, daemon=True):
        raise NotImplementedError

    def add_thread_finalizer(ident, func, /, *, ref=None):
        raise NotImplementedError

    def remove_thread_finalizer(ident, key, /):
        raise NotImplementedError

else:
    import atexit
    import weakref

    from logging import getLogger
    from collections import deque

    from . import thread as _thread

    LOGGER = getLogger(__name__)

    threads = set()

    finalizers = {}
    finalizers_lock = allocate_lock()

    shutdown_locks = deque()

    try:
        ThreadLocal = _thread._local
    except AttributeError:
        object___new__ = object.__new__
        object___dir__ = object.__dir__
        object___getattribute__ = object.__getattribute__
        object___setattr__ = object.__setattr__
        object___delattr__ = object.__delattr__

        def get_thread_namespace(self, /, *, init=False):
            namespaces = object___getattribute__(self, "_namespaces_")

            if (ident := get_ident()) in threads:
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

                    namespace = namespaces[thread_ref] = (
                        object___getattribute__(self, "_kwargs_").copy()
                    )
                else:
                    namespace = None
            elif not init:
                namespace = None
            else:
                raise RuntimeError("no current thread")

            return namespace

        class ThreadLocal:
            __slots__ = (
                "__weakref__",
                "_namespaces_",
                "_kwargs_",
            )

            @staticmethod
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
                    raise AttributeError("readonly attribute")
                elif name.startswith("_") and name.endswith("_"):
                    object___setattr__(self, name, value)
                else:
                    get_thread_namespace(self, init=True)[name] = value

            def __delattr__(self, /, name):
                if name == "__dict__":
                    raise AttributeError("readonly attribute")
                elif name.startswith("_") and name.endswith("_"):
                    object___delattr__(self, name)
                else:
                    try:
                        namespace = get_thread_namespace(self, init=False)

                        if namespace is None:
                            raise KeyError

                        del namespace[name]
                    except KeyError:
                        raise AttributeError(
                            f"{self.__class__.__name__!r} object"
                            f" has no attribute {name!r}"
                        ) from None

    def run_thread_finalizer(ident, thread, /):
        if thread is not None:
            thread.join()

        while True:
            with finalizers_lock:
                if thread is not None:
                    callbacks = list(finalizers[thread].values())
                    finalizers[thread].clear()
                else:
                    callbacks = list(finalizers[ident].values())
                    finalizers[ident].clear()

                if not callbacks:
                    if thread is not None:
                        del finalizers[thread]
                    else:
                        del finalizers[ident]

                    break

            for _, func in callbacks:
                try:
                    func()
                except Exception:
                    if thread is not None:
                        thread_repr = repr(thread)
                    else:
                        thread_repr = f"<thread {ident!r}>"

                    LOGGER.exception(
                        f"exception calling callback for {thread_repr}",
                    )

    def run_new_thread(target, start_lock, shutdown_lock, /, *args, **kwargs):
        if shutdown_lock is not None:
            shutdown_locks.append(shutdown_lock)

        try:
            ident = get_ident()
            threads.add(ident)

            try:
                finalizers[ident] = {}

                try:
                    start_lock.release()
                    target(*args, **kwargs)
                finally:
                    run_thread_finalizer(ident, None)
            finally:
                threads.remove(ident)
        finally:
            if shutdown_lock is not None:
                try:
                    shutdown_locks.remove(shutdown_lock)
                except ValueError:
                    pass

                shutdown_lock.release()

    def start_new_thread(target, args=(), kwargs=MISSING, *, daemon=True):
        if not callable(target):
            raise TypeError("'target' argument must be callable")

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
            raise TypeError("'args' argument must be an iterable") from None

        if kwargs is not MISSING:
            if not isinstance(kwargs, dict):
                raise TypeError("'kwargs' argument must be a dictionary")

            ident = _thread.start_new_thread(run_new_thread, args, kwargs)
        else:
            ident = _thread.start_new_thread(run_new_thread, args)

        start_lock.acquire()

        return ident

    def add_thread_finalizer(ident, func, /, *, ref=None):
        with finalizers_lock:
            try:
                if ident is not None:
                    callbacks = finalizers[ident]
                else:
                    callbacks = finalizers[get_ident()]
            except KeyError:
                if ident is not None:
                    thread = get_thread(ident)

                    if thread is None:
                        raise RuntimeError(
                            f"no running thread {ident!r}",
                        ) from None
                else:
                    thread = current_thread()

                    if thread is None:
                        raise RuntimeError("no current thread") from None

                start_new_thread(
                    run_thread_finalizer,
                    [ident, thread],
                    daemon=False,
                )

                finalizers[thread] = callbacks = {}

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
        with finalizers_lock:
            try:
                if ident is not None:
                    callbacks = finalizers[ident]
                else:
                    callbacks = finalizers[get_ident()]
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

    @atexit.register
    def shutdown():
        while shutdown_locks:
            try:
                shutdown_lock = shutdown_locks.popleft()
            except IndexError:
                pass
            else:
                shutdown_lock.acquire()
