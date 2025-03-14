#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from abc import ABC, abstractmethod

from ._checkpoints import checkpoint, green_checkpoint
from ._libraries import current_async_library, current_green_library
from ._threads import once

object___new__ = object.__new__


class Event(ABC):
    __slots__ = ()

    @abstractmethod
    def __bool__(self, /):
        return self.is_set()

    @abstractmethod
    def set(self, /):
        raise NotImplementedError

    @abstractmethod
    def is_set(self, /):
        raise NotImplementedError

    @abstractmethod
    def is_cancelled(self, /):
        raise NotImplementedError


class DummyEvent(Event):
    __slots__ = ()

    def __new__(cls, /, *, shield=False):
        return DUMMY_EVENT

    def __init_subclass__(cls, /, **kwargs):
        bcs = DummyEvent
        bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

        msg = f"type '{bcs_repr}' is not an acceptable base type"
        raise TypeError(msg)

    def __reduce__(self, /):
        return "DUMMY_EVENT"

    def __repr__(self, /):
        return f"{self.__class__.__module__}.DUMMY_EVENT"

    def __bool__(self, /):
        return True

    def __await__(self, /):
        yield from checkpoint().__await__()

        return True

    def wait(self, /, timeout=None):
        green_checkpoint()

        return True

    def set(self, /):
        return False

    def is_set(self, /):
        return True

    def is_cancelled(self, /):
        return False


DUMMY_EVENT = object___new__(DummyEvent)


class GreenEvent(Event):
    __slots__ = ()

    def __new__(cls, /, *, shield=False):
        if cls is GreenEvent:
            library = current_green_library()

            if library == "threading":
                imp = _ThreadingEvent
            elif library == "eventlet":
                imp = _EventletEvent
            elif library == "gevent":
                imp = _GeventEvent
            else:
                msg = f"unsupported green library {library!r}"
                raise RuntimeError(msg)

            return imp.__new__(imp, shield)

        return super().__new__(cls)

    @abstractmethod
    def wait(self, /, timeout=None):
        raise NotImplementedError


class AsyncEvent(Event):
    __slots__ = ()

    def __new__(cls, /, *, shield=False):
        if cls is AsyncEvent:
            library = current_async_library()

            if library == "asyncio":
                imp = _AsyncioEvent
            elif library == "curio":
                imp = _CurioEvent
            elif library == "trio":
                imp = _TrioEvent
            else:
                msg = f"unsupported async library {library!r}"
                raise RuntimeError(msg)

            return imp.__new__(imp, shield)

        return super().__new__(cls)

    @abstractmethod
    def __await__(self, /):
        raise NotImplementedError


class _ThreadingEvent(GreenEvent):
    __slots__ = ()

    def __new__(cls, /, shield=False):
        imp = get_threading_event_class()

        return imp.__new__(imp, shield)

    def __init_subclass__(cls, /, **kwargs):
        bcs = _ThreadingEvent
        bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

        msg = f"type '{bcs_repr}' is not an acceptable base type"
        raise TypeError(msg)


class _EventletEvent(GreenEvent):
    __slots__ = ()

    def __new__(cls, /, shield=False):
        imp = get_eventlet_event_class()

        return imp.__new__(imp, shield)

    def __init_subclass__(cls, /, **kwargs):
        bcs = _EventletEvent
        bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

        msg = f"type '{bcs_repr}' is not an acceptable base type"
        raise TypeError(msg)


class _GeventEvent(GreenEvent):
    __slots__ = ()

    def __new__(cls, /, shield=False):
        imp = get_gevent_event_class()

        return imp.__new__(imp, shield)

    def __init_subclass__(cls, /, **kwargs):
        bcs = _GeventEvent
        bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

        msg = f"type '{bcs_repr}' is not an acceptable base type"
        raise TypeError(msg)


class _AsyncioEvent(AsyncEvent):
    __slots__ = ()

    def __new__(cls, /, shield=False):
        imp = get_asyncio_event_class()

        return imp.__new__(imp, shield)

    def __init_subclass__(cls, /, **kwargs):
        bcs = _AsyncioEvent
        bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

        msg = f"type '{bcs_repr}' is not an acceptable base type"
        raise TypeError(msg)


class _CurioEvent(AsyncEvent):
    __slots__ = ()

    def __new__(cls, /, shield=False):
        imp = get_curio_event_class()

        return imp.__new__(imp, shield)

    def __init_subclass__(cls, /, **kwargs):
        bcs = _CurioEvent
        bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

        msg = f"type '{bcs_repr}' is not an acceptable base type"
        raise TypeError(msg)


class _TrioEvent(AsyncEvent):
    __slots__ = ()

    def __new__(cls, /, shield=False):
        imp = get_trio_event_class()

        return imp.__new__(imp, shield)

    def __init_subclass__(cls, /, **kwargs):
        bcs = _TrioEvent
        bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

        msg = f"type '{bcs_repr}' is not an acceptable base type"
        raise TypeError(msg)


@once
def get_threading_event_class():
    global _ThreadingEvent

    from . import _checkpoints as _cp, _monkey
    from ._thread import allocate_lock

    if _monkey._eventlet_patched("time"):
        sleep = _monkey._import_eventlet_original("time").sleep
    elif _monkey._gevent_patched("time"):
        sleep = _monkey._import_gevent_original("time").sleep
    else:
        sleep = _monkey._import_python_original("time").sleep

    class _ThreadingEvent(GreenEvent):
        __slots__ = (
            "__lock",
            "_is_cancelled",
            "_is_set",
            "_is_shielded",
            "_is_unset",
        )

        def __new__(cls, /, shield=False):
            self = object___new__(cls)

            self.__lock = allocate_lock()
            self.__lock.acquire()

            self._is_cancelled = False
            self._is_set = False
            self._is_shielded = shield
            self._is_unset = [True]

            return self

        def __init_subclass__(cls, /, **kwargs):
            bcs = _ThreadingEvent
            bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

            msg = f"type '{bcs_repr}' is not an acceptable base type"
            raise TypeError(msg)

        def __reduce__(self, /):
            msg = f"cannot reduce {self!r}"
            raise TypeError(msg)

        def __repr__(self, /):
            cls_repr = f"{GreenEvent.__module__}.GreenEvent[threading]"

            if self._is_set:
                state = "set"
            elif self._is_cancelled:
                state = "cancelled"
            elif self._is_shielded:
                state = "unset (shielded)"
            else:
                state = "unset"

            return f"<{cls_repr} object at {id(self):#x}: {state}>"

        def __bool__(self, /):
            return self._is_set

        def wait(self, /, timeout=None):
            if self._is_set or self._is_cancelled:
                if _cp.threading_checkpoints_cvar.get():
                    sleep(0)

                return True

            try:
                if timeout is None or self._is_shielded:
                    return self.__lock.acquire()
                elif timeout > 0:
                    return self.__lock.acquire(True, timeout)
                else:
                    return self.__lock.acquire(False)
            finally:
                if not self._is_set:
                    try:
                        self._is_unset.pop()
                    except IndexError:
                        self._is_set = True
                    else:
                        self._is_cancelled = True

        def set(self, /):
            if self._is_set or self._is_cancelled:
                return False

            try:
                self._is_unset.pop()
            except IndexError:
                return False
            else:
                self._is_set = True

            self.__lock.release()

            return True

        def is_set(self, /):
            return self._is_set

        def is_cancelled(self, /):
            return self._is_cancelled

    return _ThreadingEvent


@once
def get_eventlet_event_class():
    global _EventletEvent

    from eventlet import sleep
    from eventlet.hubs import _threadlocal, get_hub
    from greenlet import getcurrent

    from . import _checkpoints as _cp, _patcher

    _patcher.patch_eventlet()

    class _EventletEvent(GreenEvent):
        __slots__ = (
            "__greenlet",
            "__hub",
            "_is_cancelled",
            "_is_set",
            "_is_shielded",
            "_is_unset",
        )

        def __new__(cls, /, shield=False):
            self = object___new__(cls)

            self.__greenlet = None
            self.__hub = get_hub()

            self._is_cancelled = False
            self._is_set = False
            self._is_shielded = shield
            self._is_unset = [True]

            return self

        def __init_subclass__(cls, /, **kwargs):
            bcs = _EventletEvent
            bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

            msg = f"type '{bcs_repr}' is not an acceptable base type"
            raise TypeError(msg)

        def __reduce__(self, /):
            msg = f"cannot reduce {self!r}"
            raise TypeError(msg)

        def __repr__(self, /):
            cls_repr = f"{GreenEvent.__module__}.GreenEvent[eventlet]"

            if self._is_set:
                state = "set"
            elif self._is_cancelled:
                state = "cancelled"
            elif self._is_shielded:
                state = "unset (shielded)"
            else:
                state = "unset"

            return f"<{cls_repr} object at {id(self):#x}: {state}>"

        def __bool__(self, /):
            return self._is_set

        def wait(self, /, timeout=None):
            if self._is_set or self._is_cancelled:
                if _cp.eventlet_checkpoints_cvar.get():
                    sleep()

                return True

            try:
                self.__greenlet = getcurrent()

                try:
                    hub = self.__hub

                    if timeout is None or self._is_shielded:
                        timer = None
                    elif timeout > 0:
                        timer = hub.schedule_call_local(timeout, self.__cancel)
                    else:
                        timer = hub.schedule_call_local(0, self.__cancel)

                    try:
                        if self._is_shielded:
                            return _cp._eventlet_repeat_if_cancelled(
                                hub.switch,
                                (),
                                {},
                            )
                        else:
                            return hub.switch()
                    finally:
                        if timer is not None:
                            timer.cancel()
                finally:
                    self.__greenlet = None
            finally:
                if not self._is_set:
                    try:
                        self._is_unset.pop()
                    except IndexError:
                        self._is_set = True
                    else:
                        self._is_cancelled = True

        def __set(self, /):
            if self.__greenlet is not None:
                self.__greenlet.switch(True)

        def __cancel(self, /):
            if self.__greenlet is not None:
                self.__greenlet.switch(False)

        def set(self, /):
            if self._is_set or self._is_cancelled:
                return False

            try:
                self._is_unset.pop()
            except IndexError:
                return False
            else:
                self._is_set = True

            try:
                current_hub = _threadlocal.hub
            except AttributeError:  # no running hub
                current_hub = None

            if current_hub is self.__hub:
                self.__hub.schedule_call_global(0, self.__set)
            else:
                self.__hub.schedule_call_threadsafe(0, self.__set)

            return True

        def is_set(self, /):
            return self._is_set

        def is_cancelled(self, /):
            return self._is_cancelled

    return _EventletEvent


@once
def get_gevent_event_class():
    global _GeventEvent

    from gevent import get_hub, sleep
    from gevent._hub_local import get_hub_if_exists
    from greenlet import getcurrent

    from . import _checkpoints as _cp

    def noop():
        pass

    class _GeventEvent(GreenEvent):
        __slots__ = (
            "__greenlet",
            "__hub",
            "_is_cancelled",
            "_is_set",
            "_is_shielded",
            "_is_unset",
        )

        def __new__(cls, /, shield=False):
            self = object___new__(cls)

            self.__greenlet = None
            self.__hub = get_hub()

            self._is_cancelled = False
            self._is_set = False
            self._is_shielded = shield
            self._is_unset = [True]

            return self

        def __init_subclass__(cls, /, **kwargs):
            bcs = _GeventEvent
            bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

            msg = f"type '{bcs_repr}' is not an acceptable base type"
            raise TypeError(msg)

        def __reduce__(self, /):
            msg = f"cannot reduce {self!r}"
            raise TypeError(msg)

        def __repr__(self, /):
            cls_repr = f"{GreenEvent.__module__}.GreenEvent[gevent]"

            if self._is_set:
                state = "set"
            elif self._is_cancelled:
                state = "cancelled"
            elif self._is_shielded:
                state = "unset (shielded)"
            else:
                state = "unset"

            return f"<{cls_repr} object at {id(self):#x}: {state}>"

        def __bool__(self, /):
            return self._is_set

        def wait(self, /, timeout=None):
            if self._is_set or self._is_cancelled:
                if _cp.gevent_checkpoints_cvar.get():
                    sleep()

                return True

            try:
                self.__greenlet = getcurrent()

                try:
                    hub = self.__hub

                    if timeout is None or self._is_shielded:
                        timer = None
                    else:
                        if timeout > 0:
                            timer = hub.loop.timer(timeout)
                        else:
                            timer = hub.loop.timer(0)

                        timer.start(self.__cancel, update=True)

                    try:
                        watcher = hub.loop.async_()  # avoid LoopExit
                        watcher.start(noop)

                        try:
                            if self._is_shielded:
                                return _cp._gevent_repeat_if_cancelled(
                                    hub.switch,
                                    (),
                                    {},
                                )
                            else:
                                return hub.switch()
                        finally:
                            watcher.close()
                    finally:
                        if timer is not None:
                            timer.close()
                finally:
                    self.__greenlet = None
            finally:
                if not self._is_set:
                    try:
                        self._is_unset.pop()
                    except IndexError:
                        self._is_set = True
                    else:
                        self._is_cancelled = True

        def __set(self, /):
            if self.__greenlet is not None:
                self.__greenlet.switch(True)

        def __cancel(self, /):
            if self.__greenlet is not None:
                self.__greenlet.switch(False)

        def set(self, /):
            if self._is_set or self._is_cancelled:
                return False

            try:
                self._is_unset.pop()
            except IndexError:
                return False
            else:
                self._is_set = True

            current_hub = get_hub_if_exists()

            try:
                if current_hub is self.__hub:
                    self.__hub.loop.run_callback(self.__set)
                else:
                    self.__hub.loop.run_callback_threadsafe(self.__set)
            except ValueError:  # event loop is destroyed
                pass

            return True

        def is_set(self, /):
            return self._is_set

        def is_cancelled(self, /):
            return self._is_cancelled

    return _GeventEvent


@once
def get_asyncio_event_class():
    global _AsyncioEvent

    from asyncio import InvalidStateError, get_running_loop, shield, sleep

    from . import _checkpoints as _cp

    class _AsyncioEvent(AsyncEvent):
        __slots__ = (
            "__future",
            "__loop",
            "_is_cancelled",
            "_is_set",
            "_is_shielded",
            "_is_unset",
        )

        def __new__(cls, /, shield=False):
            self = object___new__(cls)

            self.__future = None
            self.__loop = get_running_loop()

            self._is_cancelled = False
            self._is_set = False
            self._is_shielded = shield
            self._is_unset = [True]

            return self

        def __init_subclass__(cls, /, **kwargs):
            bcs = _AsyncioEvent
            bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

            msg = f"type '{bcs_repr}' is not an acceptable base type"
            raise TypeError(msg)

        def __reduce__(self, /):
            msg = f"cannot reduce {self!r}"
            raise TypeError(msg)

        def __repr__(self, /):
            cls_repr = f"{AsyncEvent.__module__}.AsyncEvent[asyncio]"

            if self._is_set:
                state = "set"
            elif self._is_cancelled:
                state = "cancelled"
            elif self._is_shielded:
                state = "unset (shielded)"
            else:
                state = "unset"

            return f"<{cls_repr} object at {id(self):#x}: {state}>"

        def __bool__(self, /):
            return self._is_set

        def __await__(self, /):
            if self._is_set or self._is_cancelled:
                if _cp.asyncio_checkpoints_cvar.get():
                    yield from sleep(0).__await__()

                return True

            try:
                self.__future = self.__loop.create_future()

                try:
                    if self._is_shielded:
                        yield from _cp._asyncio_repeat_if_cancelled(
                            shield,
                            [self.__future],
                            {},
                        ).__await__()
                    else:
                        yield from self.__future.__await__()
                finally:
                    self.__future = None
            finally:
                if not self._is_set:
                    try:
                        self._is_unset.pop()
                    except IndexError:
                        self._is_set = True
                    else:
                        self._is_cancelled = True

            return True

        def __set(self, /):
            if self.__future is not None:
                try:
                    self.__future.set_result(True)
                except InvalidStateError:  # future is cancelled
                    pass

        def set(self, /):
            if self._is_set or self._is_cancelled:
                return False

            try:
                self._is_unset.pop()
            except IndexError:
                return False
            else:
                self._is_set = True

            try:
                current_loop = get_running_loop()
            except RuntimeError:  # no running event loop
                current_loop = None

            if current_loop is self.__loop:
                self.__set()
            else:
                try:
                    self.__loop.call_soon_threadsafe(self.__set)
                except RuntimeError:  # event loop is closed
                    pass

            return True

        def is_set(self, /):
            return self._is_set

        def is_cancelled(self, /):
            return self._is_cancelled

    return _AsyncioEvent


@once
def get_curio_event_class():
    global _CurioEvent

    from concurrent.futures import Future, InvalidStateError

    from curio import check_cancellation, sleep
    from curio.traps import _future_wait

    from . import _checkpoints as _cp

    class _CurioEvent(AsyncEvent):
        __slots__ = (
            "__future",
            "_is_cancelled",
            "_is_set",
            "_is_shielded",
            "_is_unset",
        )

        def __new__(cls, /, shield=False):
            self = object___new__(cls)

            self.__future = None

            self._is_cancelled = False
            self._is_set = False
            self._is_shielded = shield
            self._is_unset = [True]

            return self

        def __init_subclass__(cls, /, **kwargs):
            bcs = _CurioEvent
            bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

            msg = f"type '{bcs_repr}' is not an acceptable base type"
            raise TypeError(msg)

        def __reduce__(self, /):
            msg = f"cannot reduce {self!r}"
            raise TypeError(msg)

        def __repr__(self, /):
            cls_repr = f"{AsyncEvent.__module__}.AsyncEvent[curio]"

            if self._is_set:
                state = "set"
            elif self._is_cancelled:
                state = "cancelled"
            elif self._is_shielded:
                state = "unset (shielded)"
            else:
                state = "unset"

            return f"<{cls_repr} object at {id(self):#x}: {state}>"

        def __bool__(self, /):
            return self._is_set

        def __await__(self, /):
            if self._is_set or self._is_cancelled:
                if _cp.curio_checkpoints_cvar.get():
                    yield from sleep(0).__await__()

                return True

            try:
                self.__future = Future()

                try:
                    if self._is_shielded:
                        yield from _cp._curio_repeat_if_cancelled(
                            _future_wait,
                            [self.__future],
                            {},
                        ).__await__()
                        yield from check_cancellation().__await__()
                    else:
                        yield from _future_wait(self.__future).__await__()
                finally:
                    self.__future = None
            finally:
                if not self._is_set:
                    try:
                        self._is_unset.pop()
                    except IndexError:
                        self._is_set = True
                    else:
                        self._is_cancelled = True

            return True

        def set(self, /):
            if self._is_set or self._is_cancelled:
                return False

            try:
                self._is_unset.pop()
            except IndexError:
                return False
            else:
                self._is_set = True

            future = self.__future

            if future is not None:
                try:
                    future.set_result(True)
                except InvalidStateError:  # future is cancelled
                    pass

            return True

        def is_set(self, /):
            return self._is_set

        def is_cancelled(self, /):
            return self._is_cancelled

    return _CurioEvent


@once
def get_trio_event_class():
    global _TrioEvent

    from trio import RunFinishedError
    from trio.lowlevel import (
        Abort,
        checkpoint,
        current_task,
        current_trio_token,
        reschedule,
        wait_task_rescheduled,
    )

    from . import _checkpoints as _cp

    class _TrioEvent(AsyncEvent):
        __slots__ = (
            "__task",
            "__token",
            "_is_cancelled",
            "_is_set",
            "_is_shielded",
            "_is_unset",
        )

        def __new__(cls, /, shield=False):
            self = object___new__(cls)

            self.__task = None
            self.__token = current_trio_token()

            self._is_cancelled = False
            self._is_set = False
            self._is_shielded = shield
            self._is_unset = [True]

            return self

        def __init_subclass__(cls, /, **kwargs):
            bcs = _TrioEvent
            bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

            msg = f"type '{bcs_repr}' is not an acceptable base type"
            raise TypeError(msg)

        def __reduce__(self, /):
            msg = f"cannot reduce {self!r}"
            raise TypeError(msg)

        def __repr__(self, /):
            cls_repr = f"{AsyncEvent.__module__}.AsyncEvent[trio]"

            if self._is_set:
                state = "set"
            elif self._is_cancelled:
                state = "cancelled"
            elif self._is_shielded:
                state = "unset (shielded)"
            else:
                state = "unset"

            return f"<{cls_repr} object at {id(self):#x}: {state}>"

        def __bool__(self, /):
            return self._is_set

        def __await__(self, /):
            if self._is_set or self._is_cancelled:
                if _cp.trio_checkpoints_cvar.get():
                    yield from checkpoint().__await__()

                return True

            self.__task = current_task()

            if self._is_shielded:
                yield from _cp._trio_repeat_if_cancelled(
                    wait_task_rescheduled,
                    [self.__abort],
                    {},
                ).__await__()
            else:
                yield from wait_task_rescheduled(self.__abort).__await__()

            self.__task = None

            return True

        def __abort(self, /, raise_cancel):
            self.__task = None

            if not self._is_set:
                try:
                    self._is_unset.pop()
                except IndexError:
                    self._is_set = True
                else:
                    self._is_cancelled = True

            return Abort.SUCCEEDED

        def __set(self, /):
            if self.__task is not None:
                reschedule(self.__task)

        def set(self, /):
            if self._is_set or self._is_cancelled:
                return False

            try:
                self._is_unset.pop()
            except IndexError:
                return False
            else:
                self._is_set = True

            try:
                current_token = current_trio_token()
            except RuntimeError:  # no called trio.run()
                current_token = None

            if current_token is self.__token:
                self.__set()
            else:
                try:
                    self.__token.run_sync_soon(self.__set)
                except RunFinishedError:  # trio.run() is finished
                    pass

            return True

        def is_set(self, /):
            return self._is_set

        def is_cancelled(self, /):
            return self._is_cancelled

    return _TrioEvent
