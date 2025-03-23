#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from abc import ABC, abstractmethod

from ._checkpoints import async_checkpoint, green_checkpoint
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

    @property
    @abstractmethod
    def shield(self, /):
        raise NotImplementedError

    @shield.setter
    @abstractmethod
    def shield(self, /, value):
        raise NotImplementedError


class SetEvent(Event):
    __slots__ = ()

    def __new__(cls, /):
        return SET_EVENT

    def __init_subclass__(cls, /, **kwargs):
        bcs = SetEvent
        bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

        msg = f"type '{bcs_repr}' is not an acceptable base type"
        raise TypeError(msg)

    def __reduce__(self, /):
        return "SET_EVENT"

    def __repr__(self, /):
        return f"{self.__class__.__module__}.SET_EVENT"

    def __bool__(self, /):
        return True

    def __await__(self, /):
        yield from async_checkpoint().__await__()

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

    @property
    def shield(self, /):
        return False

    @shield.setter
    def shield(self, /, value):
        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        msg = f"'{cls_repr}' object attribute 'shield' is read-only"
        raise AttributeError(msg)


class DummyEvent(Event):
    __slots__ = ()

    def __new__(cls, /):
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
        yield from async_checkpoint().__await__()

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

    @property
    def shield(self, /):
        return False

    @shield.setter
    def shield(self, /, value):
        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        msg = f"'{cls_repr}' object attribute 'shield' is read-only"
        raise AttributeError(msg)


class CancelledEvent(Event):
    __slots__ = ()

    def __new__(cls, /):
        return CANCELLED_EVENT

    def __init_subclass__(cls, /, **kwargs):
        bcs = CancelledEvent
        bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

        msg = f"type '{bcs_repr}' is not an acceptable base type"
        raise TypeError(msg)

    def __reduce__(self, /):
        return "CANCELLED_EVENT"

    def __repr__(self, /):
        return f"{self.__class__.__module__}.CANCELLED_EVENT"

    def __bool__(self, /):
        return False

    def __await__(self, /):
        yield from async_checkpoint().__await__()

        return False

    def wait(self, /, timeout=None):
        green_checkpoint()

        return False

    def set(self, /):
        return False

    def is_set(self, /):
        return False

    def is_cancelled(self, /):
        return True

    @property
    def shield(self, /):
        return False

    @shield.setter
    def shield(self, /, value):
        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        msg = f"'{cls_repr}' object attribute 'shield' is read-only"
        raise AttributeError(msg)


SET_EVENT = object___new__(SetEvent)
DUMMY_EVENT = object___new__(DummyEvent)
CANCELLED_EVENT = object___new__(CancelledEvent)


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
        imp = _get_threading_event_class()

        return imp.__new__(imp, shield)

    def __init_subclass__(cls, /, **kwargs):
        bcs = _ThreadingEvent
        bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

        msg = f"type '{bcs_repr}' is not an acceptable base type"
        raise TypeError(msg)


class _EventletEvent(GreenEvent):
    __slots__ = ()

    def __new__(cls, /, shield=False):
        imp = _get_eventlet_event_class()

        return imp.__new__(imp, shield)

    def __init_subclass__(cls, /, **kwargs):
        bcs = _EventletEvent
        bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

        msg = f"type '{bcs_repr}' is not an acceptable base type"
        raise TypeError(msg)


class _GeventEvent(GreenEvent):
    __slots__ = ()

    def __new__(cls, /, shield=False):
        imp = _get_gevent_event_class()

        return imp.__new__(imp, shield)

    def __init_subclass__(cls, /, **kwargs):
        bcs = _GeventEvent
        bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

        msg = f"type '{bcs_repr}' is not an acceptable base type"
        raise TypeError(msg)


class _AsyncioEvent(AsyncEvent):
    __slots__ = ()

    def __new__(cls, /, shield=False):
        imp = _get_asyncio_event_class()

        return imp.__new__(imp, shield)

    def __init_subclass__(cls, /, **kwargs):
        bcs = _AsyncioEvent
        bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

        msg = f"type '{bcs_repr}' is not an acceptable base type"
        raise TypeError(msg)


class _CurioEvent(AsyncEvent):
    __slots__ = ()

    def __new__(cls, /, shield=False):
        imp = _get_curio_event_class()

        return imp.__new__(imp, shield)

    def __init_subclass__(cls, /, **kwargs):
        bcs = _CurioEvent
        bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

        msg = f"type '{bcs_repr}' is not an acceptable base type"
        raise TypeError(msg)


class _TrioEvent(AsyncEvent):
    __slots__ = ()

    def __new__(cls, /, shield=False):
        imp = _get_trio_event_class()

        return imp.__new__(imp, shield)

    def __init_subclass__(cls, /, **kwargs):
        bcs = _TrioEvent
        bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

        msg = f"type '{bcs_repr}' is not an acceptable base type"
        raise TypeError(msg)


@once
def _get_threading_event_class():
    global _ThreadingEvent

    from . import _checkpoints as _cp, _time
    from ._thread import allocate_lock

    class _ThreadingEvent(GreenEvent):
        __slots__ = (
            "__lock",
            "_is_cancelled",
            "_is_set",
            "_is_unset",
            "shield",
        )

        def __new__(cls, /, shield=False):
            self = object___new__(cls)

            self.__lock = None

            self._is_cancelled = False
            self._is_set = False
            self._is_unset = [True]

            self.shield = shield

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
            else:
                state = "unset"

            return f"<{cls_repr} object at {id(self):#x}: {state}>"

        def __bool__(self, /):
            return self._is_set

        def wait(self, /, timeout=None):
            if self._is_set:
                if _cp._threading_checkpoints_enabled():
                    _time._threading_sleep(0)

                return True

            if self._is_cancelled:
                if _cp._threading_checkpoints_enabled():
                    _time._threading_sleep(0)

                return False

            lock = allocate_lock()
            lock.acquire()

            self.__lock = lock

            try:
                if self._is_set:
                    if _cp._threading_checkpoints_enabled():
                        _time._threading_sleep(0)

                    return True

                try:
                    if timeout is None or self.shield:
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
            finally:
                self.__lock = None

        def set(self, /):
            if self._is_set or self._is_cancelled:
                return False

            try:
                self._is_unset.pop()
            except IndexError:
                return False
            else:
                self._is_set = True

            if (lock := self.__lock) is not None:
                lock.release()

            return True

        def is_set(self, /):
            return self._is_set

        def is_cancelled(self, /):
            return self._is_cancelled

    return _ThreadingEvent


@once
def _get_eventlet_event_class():
    global _EventletEvent

    from eventlet.hubs import _threadlocal, get_hub
    from greenlet import getcurrent

    from . import _checkpoints as _cp, _patcher, _tasks, _time

    _patcher.patch_eventlet()

    class _EventletEvent(GreenEvent):
        __slots__ = (
            "__greenlet",
            "__hub",
            "_is_cancelled",
            "_is_set",
            "_is_unset",
            "shield",
        )

        def __new__(cls, /, shield=False):
            self = object___new__(cls)

            self.__greenlet = None
            self.__hub = None

            self._is_cancelled = False
            self._is_set = False
            self._is_unset = [True]

            self.shield = shield

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
            else:
                state = "unset"

            return f"<{cls_repr} object at {id(self):#x}: {state}>"

        def __bool__(self, /):
            return self._is_set

        def wait(self, /, timeout=None):
            if self._is_set:
                if _cp._eventlet_checkpoints_enabled():
                    _time._eventlet_sleep()

                return True

            if self._is_cancelled:
                if _cp._eventlet_checkpoints_enabled():
                    _time._eventlet_sleep()

                return False

            self.__hub = get_hub()

            try:
                if self._is_set:
                    if _cp._eventlet_checkpoints_enabled():
                        _time._eventlet_sleep()

                    return True

                try:
                    self.__greenlet = getcurrent()

                    try:
                        if timeout is None or self.shield:
                            timer = None
                        elif timeout > 0:
                            timer = self.__hub.schedule_call_local(
                                timeout,
                                self.__greenlet.switch,
                                False,
                            )
                        else:
                            timer = self.__hub.schedule_call_local(
                                0,
                                self.__greenlet.switch,
                                False,
                            )

                        try:
                            if self.shield:
                                return _tasks._eventlet_shield(
                                    self.__hub,
                                    None,
                                    None,
                                )
                            else:
                                return self.__hub.switch()
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
            finally:
                self.__hub = None

        def __notify(self, /):
            if self.__greenlet is not None:
                self.__greenlet.switch(True)

        def set(self, /):
            if self._is_set or self._is_cancelled:
                return False

            try:
                self._is_unset.pop()
            except IndexError:
                return False
            else:
                self._is_set = True

            if (actual_hub := self.__hub) is not None:
                current_hub = getattr(_threadlocal, "hub", None)

                if current_hub is actual_hub:
                    actual_hub.schedule_call_global(0, self.__notify)
                else:
                    actual_hub.schedule_call_threadsafe(0, self.__notify)

            return True

        def is_set(self, /):
            return self._is_set

        def is_cancelled(self, /):
            return self._is_cancelled

    return _EventletEvent


@once
def _get_gevent_event_class():
    global _GeventEvent

    from gevent import get_hub
    from gevent._hub_local import get_hub_if_exists
    from greenlet import getcurrent

    from . import _checkpoints as _cp, _tasks, _time

    def noop():
        pass

    class _GeventEvent(GreenEvent):
        __slots__ = (
            "__greenlet",
            "__hub",
            "_is_cancelled",
            "_is_set",
            "_is_unset",
            "shield",
        )

        def __new__(cls, /, shield=False):
            self = object___new__(cls)

            self.__greenlet = None
            self.__hub = None

            self._is_cancelled = False
            self._is_set = False
            self._is_unset = [True]

            self.shield = shield

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
            else:
                state = "unset"

            return f"<{cls_repr} object at {id(self):#x}: {state}>"

        def __bool__(self, /):
            return self._is_set

        def wait(self, /, timeout=None):
            if self._is_set:
                if _cp._gevent_checkpoints_enabled():
                    _time._gevent_sleep()

                return True

            if self._is_cancelled:
                if _cp._gevent_checkpoints_enabled():
                    _time._gevent_sleep()

                return False

            self.__hub = get_hub()

            try:
                if self._is_set:
                    if _cp._gevent_checkpoints_enabled():
                        _time._gevent_sleep()

                    return True

                try:
                    self.__greenlet = getcurrent()

                    try:
                        if timeout is None or self.shield:
                            timer = None
                        else:
                            if timeout > 0:
                                timer = self.__hub.loop.timer(timeout)
                            else:
                                timer = self.__hub.loop.timer(0)

                            timer.start(
                                self.__greenlet.switch,
                                False,
                                update=True,
                            )

                        try:
                            watcher = self.__hub.loop.async_()
                            watcher.start(noop)  # avoid LoopExit

                            try:
                                if self.shield:
                                    return _tasks._gevent_shield(
                                        self.__hub,
                                        None,
                                        None,
                                    )
                                else:
                                    return self.__hub.switch()
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
            finally:
                self.__hub = None

        def __notify(self, /):
            if self.__greenlet is not None:
                self.__greenlet.switch(True)

        def set(self, /):
            if self._is_set or self._is_cancelled:
                return False

            try:
                self._is_unset.pop()
            except IndexError:
                return False
            else:
                self._is_set = True

            if (actual_hub := self.__hub) is not None:
                current_hub = get_hub_if_exists()

                try:
                    if current_hub is actual_hub:
                        actual_hub.loop.run_callback(self.__notify)
                    else:
                        actual_hub.loop.run_callback_threadsafe(self.__notify)
                except ValueError:  # event loop is destroyed
                    pass

            return True

        def is_set(self, /):
            return self._is_set

        def is_cancelled(self, /):
            return self._is_cancelled

    return _GeventEvent


@once
def _get_asyncio_event_class():
    global _AsyncioEvent

    from asyncio import (
        InvalidStateError,
        _get_running_loop as get_running_loop_if_exists,
        get_running_loop,
    )

    from . import _checkpoints as _cp, _tasks, _time

    class _AsyncioEvent(AsyncEvent):
        __slots__ = (
            "__future",
            "__loop",
            "_is_cancelled",
            "_is_set",
            "_is_unset",
            "shield",
        )

        def __new__(cls, /, shield=False):
            self = object___new__(cls)

            self.__future = None
            self.__loop = None

            self._is_cancelled = False
            self._is_set = False
            self._is_unset = [True]

            self.shield = shield

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
            else:
                state = "unset"

            return f"<{cls_repr} object at {id(self):#x}: {state}>"

        def __bool__(self, /):
            return self._is_set

        def __await__(self, /):
            if self._is_set:
                if _cp._asyncio_checkpoints_enabled():
                    yield from _time._asyncio_sleep(0).__await__()

                return True

            if self._is_cancelled:
                if _cp._asyncio_checkpoints_enabled():
                    yield from _time._asyncio_sleep(0).__await__()

                return False

            self.__loop = get_running_loop()

            try:
                if self._is_set:
                    if _cp._asyncio_checkpoints_enabled():
                        yield from _time._asyncio_sleep(0).__await__()

                    return True

                try:
                    self.__future = self.__loop.create_future()

                    try:
                        if self.shield:
                            yield from _tasks._asyncio_shield(
                                self.__future,
                                None,
                                None,
                            ).__await__()
                        else:
                            yield from self.__future.__await__()
                    finally:
                        self.__future = None

                    return True
                finally:
                    if not self._is_set:
                        try:
                            self._is_unset.pop()
                        except IndexError:
                            self._is_set = True
                        else:
                            self._is_cancelled = True
            finally:
                self.__loop = None

        def __notify(self, /):
            if self.__future is not None:
                try:
                    self.__future.set_result(True)
                except InvalidStateError:  # task is cancelled
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

            if (actual_loop := self.__loop) is not None:
                current_loop = get_running_loop_if_exists()

                if current_loop is actual_loop:
                    self.__notify()
                else:
                    try:
                        actual_loop.call_soon_threadsafe(self.__notify)
                    except RuntimeError:  # event loop is closed
                        pass

            return True

        def is_set(self, /):
            return self._is_set

        def is_cancelled(self, /):
            return self._is_cancelled

    return _AsyncioEvent


@once
def _get_curio_event_class():
    global _CurioEvent

    from concurrent.futures import Future, InvalidStateError

    from curio import check_cancellation
    from curio.traps import _future_wait

    from . import _checkpoints as _cp, _tasks, _time

    class _CurioEvent(AsyncEvent):
        __slots__ = (
            "__future",
            "_is_cancelled",
            "_is_set",
            "_is_unset",
            "shield",
        )

        def __new__(cls, /, shield=False):
            self = object___new__(cls)

            self.__future = None

            self._is_cancelled = False
            self._is_set = False
            self._is_unset = [True]

            self.shield = shield

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
            else:
                state = "unset"

            return f"<{cls_repr} object at {id(self):#x}: {state}>"

        def __bool__(self, /):
            return self._is_set

        def __await__(self, /):
            if self._is_set:
                if _cp._curio_checkpoints_enabled():
                    yield from _time._curio_sleep(0).__await__()

                return True

            if self._is_cancelled:
                if _cp._curio_checkpoints_enabled():
                    yield from _time._curio_sleep(0).__await__()

                return False

            self.__future = Future()

            try:
                if self._is_set:
                    if _cp._curio_checkpoints_enabled():
                        yield from _time._curio_sleep(0).__await__()

                    return True

                try:
                    if self.shield:
                        yield from _tasks._curio_shield(
                            _future_wait,
                            [self.__future],
                            {},
                        ).__await__()
                        yield from check_cancellation().__await__()
                    else:
                        yield from _future_wait(self.__future).__await__()

                    return True
                finally:
                    if not self._is_set:
                        try:
                            self._is_unset.pop()
                        except IndexError:
                            self._is_set = True
                        else:
                            self._is_cancelled = True
            finally:
                self.__future = None

        def set(self, /):
            if self._is_set or self._is_cancelled:
                return False

            try:
                self._is_unset.pop()
            except IndexError:
                return False
            else:
                self._is_set = True

            if (future := self.__future) is not None:
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
def _get_trio_event_class():
    global _TrioEvent

    from trio import RunFinishedError
    from trio.lowlevel import (
        Abort,
        current_task,
        current_trio_token,
        reschedule,
        wait_task_rescheduled,
    )

    from . import _checkpoints as _cp, _tasks

    def abort(raise_cancel):
        return Abort.SUCCEEDED

    class _TrioEvent(AsyncEvent):
        __slots__ = (
            "__task",
            "__token",
            "_is_cancelled",
            "_is_set",
            "_is_unset",
            "shield",
        )

        def __new__(cls, /, shield=False):
            self = object___new__(cls)

            self.__task = None
            self.__token = None

            self._is_cancelled = False
            self._is_set = False
            self._is_unset = [True]

            self.shield = shield

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
            else:
                state = "unset"

            return f"<{cls_repr} object at {id(self):#x}: {state}>"

        def __bool__(self, /):
            return self._is_set

        def __await__(self, /):
            if self._is_set:
                if _cp._trio_checkpoints_enabled():
                    yield from _cp._trio_checkpoint().__await__()

                return True

            if self._is_cancelled:
                if _cp._trio_checkpoints_enabled():
                    yield from _cp._trio_checkpoint().__await__()

                return False

            self.__token = current_trio_token()

            try:
                if self._is_set:
                    if _cp._trio_checkpoints_enabled():
                        yield from _cp._trio_checkpoint().__await__()

                    return True

                try:
                    self.__task = current_task()

                    try:
                        if self.shield:
                            yield from _tasks._trio_shield(
                                wait_task_rescheduled,
                                [abort],
                                {},
                            ).__await__()
                        else:
                            yield from wait_task_rescheduled(abort).__await__()
                    finally:
                        self.__task = None
                finally:
                    if not self._is_set:
                        try:
                            self._is_unset.pop()
                        except IndexError:
                            self._is_set = True
                        else:
                            self._is_cancelled = True
            finally:
                self.__token = None

            return True

        def __notify(self, /):
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

            if (actual_token := self.__token) is not None:
                try:
                    current_token = current_trio_token()
                except RuntimeError:  # no called trio.run()
                    current_token = None

                if current_token is actual_token:
                    self.__notify()
                else:
                    try:
                        actual_token.run_sync_soon(self.__notify)
                    except RunFinishedError:  # trio.run() is finished
                        pass

            return True

        def is_set(self, /):
            return self._is_set

        def is_cancelled(self, /):
            return self._is_cancelled

    return _TrioEvent
