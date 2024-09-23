#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

__all__ = (
    "patch_threading",
    "patch_eventlet",
)

import sys
import platform

from sys import modules
from functools import partial, wraps
from importlib import import_module

PYTHON_VERSION = sys.version_info
PYTHON_IMPLEMENTATION = platform.python_implementation()


def eventlet_patched(name, /):
    global eventlet_patched

    if "eventlet" in modules:
        try:
            from eventlet import patcher
            from eventlet.patcher import already_patched, original
        except ImportError:

            def eventlet_patched(name, /):
                return None

        else:
            # eventlet stores information about patched modules not by their
            # names, but by keyword name, so is_monkey_patched() will not work
            # for module names

            def generate_mapping():
                mapping = {}

                for name, value in vars(patcher).items():
                    if name.startswith("_green_") and (
                        name.endswith("_modules") or name.count("_") == 2
                    ):
                        module_key = name[7:].partition("_")[0]

                        for module_name, module in value():
                            mapping[module_name] = module_key

                return mapping

            mapping = generate_mapping()

            def eventlet_patched(name, /):
                module_name, _, attribute_name = name.partition(":")

                if (
                    module_name in mapping
                    and mapping[module_name] in already_patched
                ):
                    if attribute_name:
                        patched_module = import_module(module_name)

                        try:
                            value = getattr(patched_module, attribute_name)
                        except AttributeError:
                            answer = hasattr(
                                original(module_name),
                                attribute_name,
                            )
                        else:
                            try:
                                value_module = value.__module__
                            except AttributeError:
                                answer = None
                            else:
                                answer = value_module.partition(".")[0] == (
                                    "eventlet"
                                )
                    else:
                        answer = True
                else:
                    answer = False

                return answer

        answer = eventlet_patched(name)
    else:
        answer = False

    return answer


def gevent_patched(name, /):
    global gevent_patched

    if "gevent" in modules:
        try:
            from gevent.monkey import saved
        except ImportError:

            def gevent_patched(name, /):
                return None

        else:
            # some objects, such as threading._active_limbo_lock, are
            # replaced by gevent, but without saving the originals, so
            # is_object_patched() is not enough

            def gevent_patched(name, /):
                module_name, _, attribute_name = name.partition(":")

                if module_name in saved:
                    if (
                        attribute_name
                        and attribute_name not in saved[module_name]
                    ):
                        patched_module = import_module(module_name)

                        try:
                            value = getattr(patched_module, attribute_name)
                        except AttributeError:
                            answer = False
                        else:
                            try:
                                value_module = value.__module__
                            except AttributeError:
                                answer = None
                            else:
                                answer = value_module.partition(".")[0] == (
                                    "gevent"
                                )
                    else:
                        answer = True
                else:
                    answer = False

                return answer

        answer = gevent_patched(name)
    else:
        answer = False

    return answer


def import_eventlet_original(module_name, /):
    global import_eventlet_original

    if "eventlet" in modules:
        try:
            from eventlet.patcher import original as import_eventlet_original
        except ImportError:

            def import_eventlet_original(module_name, /):
                return None

        module = import_eventlet_original(module_name)
    else:
        module = None

    return module


def import_gevent_original(module_name, /):
    global import_gevent_original

    if "gevent" in modules:
        try:
            from gevent.monkey import saved
        except ImportError:

            def import_gevent_original(module_name, /):
                return None

        else:
            object___new__ = object.__new__
            object___getattribute__ = object.__getattribute__
            object___setattr__ = object.__setattr__

            def check_value(self, /, module, name):
                value = getattr(module, name)

                try:
                    value_module = value.__module__
                except AttributeError:
                    pass
                else:
                    if value_module.partition(".")[0] == "gevent":
                        raise AttributeError(
                            f"No original attribute named {name!r}",
                        )

                return value

            class ModuleProxy:
                __slots__ = (
                    "_module_",
                    "_name_",
                    "_content_",
                )

                @staticmethod
                def __new__(cls, /, name):
                    self = object___new__(cls)

                    object___setattr__(self, "_name_", name)
                    object___setattr__(self, "_content_", saved[name])

                    return self

                def __getnewargs__(self, /):
                    return (object___getattribute__(self, "_name_"),)

                def __repr__(self, /):
                    name = object___getattribute__(self, "_name_")

                    return f"<module {name!r} proxy>"

                def __getattribute__(self, /, name):
                    if name.startswith("_") and name.endswith("_"):
                        value = object___getattribute__(self, name)
                    else:
                        content = object___getattribute__(self, "_content_")

                        if name in content:
                            value = content[name]
                        else:
                            try:
                                module = object___getattribute__(
                                    self,
                                    "_module_",
                                )
                            except AttributeError:
                                module = import_module(
                                    object___getattribute__(
                                        self,
                                        "_name_",
                                    )
                                )

                                object___setattr__(self, "_module_", module)

                            if hasattr(module, name):
                                value = check_value(self, module, name)
                            else:
                                value = object___getattribute__(self, name)

                    return value

                def __setattr__(self, /, name, value):
                    if name.startswith("_") and name.endswith("_"):
                        object___setattr__(self, name, value)
                    else:
                        content = object___getattribute__(self, "_content_")

                        if name in content:
                            content[name] = value
                        else:
                            try:
                                module = object___getattribute__(
                                    self,
                                    "_module_",
                                )
                            except AttributeError:
                                module = import_module(
                                    object___getattribute__(
                                        self,
                                        "_name_",
                                    )
                                )

                                object___setattr__(self, "_module_", module)

                            check_value(self, module, name)
                            setattr(module, name, value)

                def __delattr__(self, /, name):
                    raise TypeError(
                        f"cannot delete {name!r} attribute of module proxy",
                    )

            def import_gevent_original(module_name, /):
                if module_name in saved and not eventlet_patched(module_name):
                    module = ModuleProxy(module_name)
                else:
                    module = None

                return module

        module = import_gevent_original(module_name)
    else:
        module = None

    return module


def import_original(name):
    module_name, _, attribute_name = name.partition(":")

    if eventlet_patched(module_name):
        module = import_eventlet_original(module_name)
    elif gevent_patched(module_name):
        module = import_gevent_original(module_name)
    else:
        module = import_module(module_name)

    if module is None:
        exc = ModuleNotFoundError(f"No original module named {module_name!r}")
        exc.name = module_name

        try:
            raise exc
        finally:
            del exc

    if attribute_name:
        try:
            value = getattr(module, attribute_name)
        except AttributeError:
            module_path = getattr(module, "__file__", None)
            exc = ImportError(
                f"cannot import name {attribute_name!r}"
                f" from {module_name!r}"
                f" ({module_path or 'unknown location'})"
            )

            exc.name = module_name
            exc.name_from = attribute_name
            exc.path = module_path

            try:
                raise exc from None
            finally:
                del exc
    else:
        value = module

    return value


try:
    from .thread import allocate_lock
except ImportError:
    import time

    def once(func):
        locks = {}
        results = {}

        @wraps(func)
        def wrapper(*args, **kwargs):
            key = (args, tuple(kwargs.items()))

            try:
                unlocked = locks[key]
            except KeyError:
                unlocked = locks.setdefault(key, [True])

            while key not in results:
                try:
                    unlocked.pop()
                except IndexError:
                    time.sleep(0)
                else:
                    try:
                        if key not in results:
                            results[key] = func(*args, **kwargs)
                    finally:
                        unlocked.append(True)

            return results[key]

        return wrapper

else:

    def once(func):
        locks = {}
        results = {}

        @wraps(func)
        def wrapper(*args, **kwargs):
            key = (args, tuple(kwargs.items()))

            try:
                lock = locks[key]
            except KeyError:
                lock = locks.setdefault(key, allocate_lock())

            if key not in results:
                with lock:
                    if key not in results:
                        results[key] = func(*args, **kwargs)

            return results[key]

        return wrapper


@once
def patch_threading():
    """
    Fixes race conditions in `Thread.join()` (`AssertionError`, `RuntimeError`)
    for PyPy.

    Code to reproduce::

        from threading import Thread, current_thread

        def func():
            thread = Thread(target=current_thread().join)
            thread.start()

        for _ in range(1000):
            thread = Thread(target=func)
            thread.start()
            thread.join()

    Why is this happening? Because `Thread.join()` implementation is not
    thread-safe (see CPython's gh-116372), and PyPy can switch execution to
    another thread right after `Lock.acquire()` (CPython can't)::

        from threading import Barrier, Lock, Thread

        lock = Lock()
        barrier = Barrier(1000)

        def func():
            barrier.wait()

            lock.acquire()
            lock.release()

            assert not lock.locked()  # succeeds on CPython, fails on PyPy

        for _ in range(1000):
            Thread(target=func).start()

    You may ask: why not just suppress `AssertionError` and `RuntimeError`?
    Well, even if the user suppresses them, the `_shutdown()` function won't.
    As a result, running threads will be killed as daemon threads::

        import time

        from threading import Thread, current_thread

        def func(i):
            try:
                thread = Thread(target=current_thread().join)
                thread.start()

                for j in range(3, 0, -1):
                    if i == 0:
                        print(f"{j}...")

                    time.sleep(1)
            finally:
                if i == 999:
                    time.sleep(0.5)  # ensure a long runtime

                    print('OK')  # will be printed on CPython, but not on PyPy

        for i in range(1000):
            thread = Thread(target=func, args=[i])
            thread.start()

    A related problem is that if a first thread calls `join()` of a second
    thread and in the first thread an exception (for example,
    `KeyboardInterrupt`) is raised, then the second thread will be killed as a
    daemon thread::

        import time

        from threading import Thread, main_thread

        blackmail = ' '.join([
            "Victor Stinner, I'll take your beer away!",
            'Muahahahahaha...',
            'Hahahahahahaha...',
            'AAAAHAHAHAHAHAHA!',
        ])

        def func():
            try:
                main_thread().join()
            finally:
                time.sleep(0.5)  # ensure a long runtime

                print(blackmail)  # will never be printed

        thread = Thread(target=func)
        thread.start()

        try:
            thread.join()
        except KeyboardInterrupt:
            pass  # PyPy doesn't wait for threads after KeyboardInterrupt

    The reason for this is that on September 27, 2021, CPython applied a fix
    for a different race condition on the same `Thread.join()` that caused
    hangs, and mostly on Windows (see bpo-21822, bpo-45274, and gh-28532).
    Actually, there are no hangs now, because threads can now kill each other.
    So the `KeyboardInterrupt` exception raised by the signal handler has
    become really dangerous. This patch doesn't undo that fix. If you really
    want safe Control-C handling, set your own signal handler.

    In Python 3.13, all of these issues have been resolved at C level as part
    of the free-threaded mode implementation (see gh-114271), so this patch
    only applies on versions below 3.13.
    """

    if PYTHON_VERSION >= (3, 13):
        return

    if PYTHON_IMPLEMENTATION != "PyPy":
        return

    def patch_thread(threading):
        if hasattr(threading, "_ThreadHandle"):
            return  # was a backport applied?

        Thread = threading.Thread

        if not hasattr(threading, "_maintain_shutdown_locks"):

            def _maintain_shutdown_locks():
                _shutdown_locks = threading._shutdown_locks
                _shutdown_locks.difference_update(
                    [lock for lock in _shutdown_locks if not lock.locked()]
                )

            threading._maintain_shutdown_locks = _maintain_shutdown_locks

            @wraps(Thread._set_tstate_lock)
            def Thread__set_tstate_lock(self):
                self._tstate_lock = threading._set_sentinel()
                self._tstate_lock.acquire()

                if not self.daemon:
                    with threading._shutdown_locks_lock:
                        threading._maintain_shutdown_locks()
                        threading._shutdown_locks.add(self._tstate_lock)

            Thread._set_tstate_lock = Thread__set_tstate_lock

        @wraps(Thread._stop)
        def Thread__stop(self):
            self._is_stopped = True

            if not self.daemon:
                if self._tstate_lock is not None:
                    with threading._shutdown_locks_lock:
                        if self._tstate_lock is not None:
                            threading._maintain_shutdown_locks()
                            self._tstate_lock = None
            else:
                self._tstate_lock = None

        Thread._stop = Thread__stop

        @wraps(Thread._wait_for_tstate_lock)
        def Thread__wait_for_tstate_lock(self, block=True, timeout=-1):
            lock = self._tstate_lock

            if lock is None:
                return

            try:
                if lock.acquire(block, timeout):
                    try:
                        lock.release()
                    except RuntimeError:
                        pass

                    self._stop()
            except:
                if lock.locked():
                    """
                    # possible mitigation (only works, and only partially,
                    # on non-Windows systems; on Windows it actually undoes
                    # gh-28532):

                    with _active_limbo_lock:
                        if self in _limbo or self._ident in _active:
                            raise  # false positive in case of abrupt stop
                    """

                    try:
                        lock.release()
                    except RuntimeError:
                        pass

                    self._stop()

                raise

        Thread._wait_for_tstate_lock = Thread__wait_for_tstate_lock

    def patch_shutdown(threading):
        if hasattr(threading, "_ThreadHandle"):
            return  # was a backport applied?

        if hasattr(threading, "_register_atexit"):

            @wraps(threading._register_atexit)
            def _register_atexit(func, *arg, **kwargs):
                _threading_atexits = threading._threading_atexits

                if threading._SHUTTING_DOWN:
                    raise RuntimeError("can't register atexit after shutdown")

                _threading_atexits.append(ate := partial(func, *arg, **kwargs))

                if threading._SHUTTING_DOWN:
                    _threading_atexits.remove(ate)

                    raise RuntimeError("can't register atexit after shutdown")

            threading._register_atexit = _register_atexit

        @wraps(threading._shutdown)
        def _shutdown():
            _main_thread = threading._main_thread
            _threading_atexits = threading._threading_atexits

            _shutdown_locks = threading._shutdown_locks
            _shutdown_locks_lock = threading._shutdown_locks_lock

            try:
                _is_main_interpreter = threading._is_main_interpreter
            except AttributeError:
                if _main_thread._is_stopped:
                    return
            else:
                if _main_thread._is_stopped and _is_main_interpreter():
                    return

            threading._SHUTTING_DOWN = True

            for atexit_call in reversed(_threading_atexits):
                atexit_call()

            _threading_atexits.clear()

            if _main_thread.ident == threading.get_ident():
                tlock = _main_thread._tstate_lock

                assert tlock is not None
                assert tlock.locked()

                tlock.release()
                _main_thread._stop()

            while True:
                with _shutdown_locks_lock:
                    locks = list(_shutdown_locks)
                    _shutdown_locks.clear()

                if not locks:
                    break

                for lock in locks:
                    lock.acquire()

                    try:
                        lock.release()
                    except RuntimeError:
                        pass

        threading._shutdown = _shutdown

    if not eventlet_patched("threading") and not gevent_patched("threading"):
        threading = import_module("threading")

        patch_thread(threading)
        patch_shutdown(threading)

    if (threading := import_eventlet_original("threading")) is not None:
        patch_thread(threading)
        patch_shutdown(threading)

    # gevent breaks original objects with changes in the module namespace,
    # so processing its originals makes no sense


@once
def patch_eventlet():
    """
    Injects `destroy()` into `BaseHub` to fix EMFILE ("too many open files")
    + ENOMEM (memory leak).

    Code to reproduce::

        from threading import Thread

        import eventlet
        import eventlet.hubs

        stop = False

        def func():
            global stop

            try:
                eventlet.sleep()
            except:
                stop = True
                raise
            finally:
                hub = eventlet.hubs.get_hub()

                try:
                    destroy = hub.destroy
                except AttributeError:
                    pass
                else:
                    destroy()

        while not stop:
            thread = Thread(target=func)
            thread.start()
            thread.join()

    Also injects `schedule_call_threadsafe()` (a thread-safe variant of
    `schedule_call_global()`).
    """

    def inject_destroy(BaseHub):
        if hasattr(BaseHub, "destroy"):
            return  # what was applied?!

        def BaseHub_destroy(self, /):
            if not self.greenlet.dead:
                self.abort(wait=True)

        BaseHub.destroy = BaseHub_destroy

        try:
            from eventlet.hubs.epolls import Hub as EpollHub
        except ImportError:
            pass
        else:

            def EpollHub_destroy(self, /):
                super(self.__class__, self).destroy()
                self.poll.close()

            EpollHub.destroy = EpollHub_destroy

        try:
            from eventlet.hubs.kqueue import Hub as KqueueHub
        except ImportError:
            pass
        else:

            def KqueueHub_destroy(self, /):
                super(self.__class__, self).destroy()
                self.kqueue.close()

            KqueueHub.destroy = KqueueHub_destroy

        try:
            from eventlet.hubs.asyncio import Hub as AsyncioHub
        except ImportError:
            pass
        else:

            def AsyncioHub_destroy(self, /):
                super(self.__class__, self).destroy()
                self.loop.close()

            AsyncioHub.destroy = AsyncioHub_destroy

    def inject_schedule_call_threadsafe(BaseHub):
        if hasattr(BaseHub, "schedule_call_threadsafe"):
            return  # what was applied?!

        from eventlet.hubs.timer import Timer

        def BaseHub_schedule_call_threadsafe(self, /, *args, **kwargs):
            timer = Timer(*args, **kwargs)
            scheduled_time = self.clock() + timer.seconds

            try:
                timers = self._aiologic_threadsafe_timers
            except AttributeError:
                timers = vars(self).setdefault(
                    "_aiologic_threadsafe_timers",
                    [],
                )

            timers.append((scheduled_time, timer))

            try:
                wsock = self._aiologic_wsock
            except AttributeError:
                pass
            else:
                try:
                    wsock.send(b"\x00")
                except OSError:
                    pass

            # timer methods are not thread-safe, so we don't return it

        BaseHub.schedule_call_threadsafe = BaseHub_schedule_call_threadsafe

        try:
            from eventlet.hubs.asyncio import Hub as AsyncioHub
        except ImportError:
            pass
        else:

            def AsyncioHub_schedule_call_threadsafe(self, /, *args, **kwargs):
                timer = Timer(*args, **kwargs)
                scheduled_time = self.clock() + timer.seconds

                try:
                    timers = self._aiologic_threadsafe_timers
                except AttributeError:
                    timers = vars(self).setdefault(
                        "_aiologic_threadsafe_timers",
                        [],
                    )

                timers.append((scheduled_time, timer))

                try:
                    self.loop.call_soon_threadsafe(self.sleep_event.set)
                except RuntimeError:  # event loop is closed
                    pass

                # timer methods are not thread-safe, so we don't return it

            AsyncioHub.schedule_call_threadsafe = (
                AsyncioHub_schedule_call_threadsafe
            )

        from .sockets import socketpair

        def BaseHub__aiologic_init_socketpair(self, /):
            if not hasattr(self, "_aiologic_rsock"):
                rsock, wsock = socketpair(blocking=False, buffering=1)
                rsock_fd = rsock.fileno()

                def rsock_recv(_, /):
                    while True:
                        try:
                            data = rsock.recv(4096)
                        except InterruptedError:
                            continue
                        except BlockingIOError:
                            break
                        else:
                            if not data:
                                break

                def rsock_throw(exc, /):
                    raise exc

                self.mark_as_reopened(rsock_fd)
                self.add(self.READ, rsock_fd, rsock_recv, rsock_throw, None)

                self._aiologic_rsock = rsock
                self._aiologic_wsock = wsock

        BaseHub._aiologic_init_socketpair = BaseHub__aiologic_init_socketpair

        try:
            from eventlet.hubs.asyncio import Hub as AsyncioHub
        except ImportError:
            pass
        else:

            def AsyncioHub__aiologic_init_socketpair(self, /):
                pass

            AsyncioHub._aiologic_init_socketpair = (
                AsyncioHub__aiologic_init_socketpair
            )

        BaseHub_prepare_timers_impl = BaseHub.prepare_timers

        @wraps(BaseHub.prepare_timers)
        def BaseHub_prepare_timers(self, /):
            self._aiologic_init_socketpair()

            try:
                timers = self._aiologic_threadsafe_timers
            except AttributeError:
                pass
            else:
                while timers:
                    items = timers.copy()

                    self.next_timers.extend(items)

                    del timers[: len(items)]

            BaseHub_prepare_timers_impl(self)

        BaseHub.prepare_timers = BaseHub_prepare_timers

        BaseHub_destroy_impl = BaseHub.destroy

        @wraps(BaseHub.destroy)
        def BaseHub_destroy(self, /):
            BaseHub_destroy_impl(self)

            try:
                rsock = self._aiologic_rsock
            except AttributeError:
                pass
            else:
                rsock.close()

            try:
                wsock = self._aiologic_wsock
            except AttributeError:
                pass
            else:
                wsock.close()

        BaseHub.destroy = BaseHub_destroy

    from eventlet.hubs.hub import BaseHub

    inject_destroy(BaseHub)
    inject_schedule_call_threadsafe(BaseHub)
