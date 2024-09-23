#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

__all__ = (
    "DUMMY_EVENT",
    "GreenEvent",
    "AsyncEvent",
)

from abc import ABC, abstractmethod

from . import patcher
from .libraries import current_async_library, current_green_library
from .checkpoints import checkpoint, green_checkpoint


class DummyEvent:
    __slots__ = ()

    @staticmethod
    def __new__(cls, /):
        if cls is DummyEvent:
            self = DUMMY_EVENT
        else:
            self = super(DummyEvent, cls).__new__(cls)

        return self

    @classmethod
    def __init_subclass__(cls, /, **kwargs):
        raise TypeError("type 'DummyEvent' is not an acceptable base type")

    def __reduce__(self, /):
        return "DUMMY_EVENT"

    def __repr__(self, /):
        return "DUMMY_EVENT"

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


DUMMY_EVENT = object.__new__(DummyEvent)


class GreenEvent(ABC):
    __slots__ = ()

    @staticmethod
    def __new__(cls, /):
        if cls is GreenEvent:
            library = current_green_library()

            if library == "threading":
                self = ThreadingEvent.__new__(ThreadingEvent)
            elif library == "eventlet":
                self = EventletEvent.__new__(EventletEvent)
            elif library == "gevent":
                self = GeventEvent.__new__(GeventEvent)
            else:
                raise RuntimeError(f"unsupported green library {library!r}")
        else:
            self = super(GreenEvent, cls).__new__(cls)

        return self

    @abstractmethod
    def __bool__(self, /):
        return self.is_set()

    @abstractmethod
    def wait(self, /, timeout=None):
        raise NotImplementedError

    @abstractmethod
    def set(self, /):
        raise NotImplementedError

    @abstractmethod
    def is_set(self, /):
        return bool(self)


def get_threading_event_class():
    global ThreadingEvent

    from .thread import allocate_lock

    class ThreadingEvent(GreenEvent):
        __slots__ = (
            "__is_unset",
            "__lock",
        )

        @staticmethod
        def __new__(cls, /):
            self = super(ThreadingEvent, cls).__new__(cls)

            self.__is_unset = [True]

            self.__lock = allocate_lock()
            self.__lock.acquire()

            return self

        @classmethod
        def __init_subclass__(cls, /, **kwargs):
            raise TypeError(
                "type 'ThreadingEvent' is not an acceptable base type",
            )

        def __reduce__(self, /):
            raise TypeError(f"cannot reduce {self!r}")

        def __bool__(self, /):
            return not self.__is_unset

        def wait(self, /, timeout=None):
            success = True

            if self.__is_unset:
                if timeout is None:
                    success = self.__lock.acquire()
                elif timeout > 0:
                    success = self.__lock.acquire(timeout=timeout)
                else:
                    success = self.__lock.acquire(blocking=False)
            else:
                green_checkpoint()

            return success

        def set(self, /):
            success = True

            if is_unset := self.__is_unset:
                try:
                    is_unset.pop()
                except IndexError:
                    success = False
                else:
                    self.__lock.release()
            else:
                success = False

            return success

        def is_set(self, /):
            return not self.__is_unset

    return ThreadingEvent


def get_eventlet_event_class():
    global EventletEvent

    from eventlet.hubs import get_hub as get_eventlet_hub
    from greenlet import getcurrent as current_greenlet

    try:
        from eventlet.hubs import _threadlocal as eventlet_hubs
    except ImportError:
        current_eventlet_hub = get_eventlet_hub
    else:

        def current_eventlet_hub():
            try:
                hub = eventlet_hubs.hub
            except AttributeError:
                hub = None

            return hub

    patcher.patch_eventlet()

    class EventletEvent(GreenEvent):
        __slots__ = (
            "__is_unset",
            "__hub",
            "__greenlet",
        )

        @staticmethod
        def __new__(cls, /):
            self = super(EventletEvent, cls).__new__(cls)

            self.__is_unset = [True]

            self.__hub = get_eventlet_hub()
            self.__greenlet = None

            return self

        @classmethod
        def __init_subclass__(cls, /, **kwargs):
            raise TypeError(
                "type 'EventletEvent' is not an acceptable base type",
            )

        def __reduce__(self, /):
            raise TypeError(f"cannot reduce {self!r}")

        def __bool__(self, /):
            return not self.__is_unset

        def wait(self, /, timeout=None):
            success = True

            if self.__is_unset:
                self.__greenlet = current_greenlet()

                try:
                    hub = self.__hub

                    if timeout is None:
                        timer = None
                    elif timeout > 0:
                        timer = hub.schedule_call_local(
                            timeout,
                            self.__set,
                            False,
                        )
                    else:
                        timer = hub.schedule_call_local(
                            0,
                            self.__set,
                            False,
                        )

                    try:
                        success = hub.switch()
                    finally:
                        if timer is not None:
                            timer.cancel()
                except BaseException:
                    if is_unset := self.__is_unset:
                        try:
                            is_unset.pop()
                        except IndexError:
                            pass

                    raise
                finally:
                    self.__greenlet = None
            else:
                green_checkpoint()

            return success

        def __set(self, /, success):
            if (greenlet := self.__greenlet) is not None:
                greenlet.switch(success)

        def set(self, /):
            success = True

            if is_unset := self.__is_unset:
                try:
                    is_unset.pop()
                except IndexError:
                    success = False
                else:
                    hub = current_eventlet_hub()

                    if hub is self.__hub:
                        hub.schedule_call_global(
                            0,
                            self.__set,
                            True,
                        )
                    else:
                        self.__hub.schedule_call_threadsafe(
                            0,
                            self.__set,
                            True,
                        )
            else:
                success = False

            return success

        def is_set(self, /):
            return not self.__is_unset

    return EventletEvent


def get_gevent_event_class():
    global GeventEvent

    from gevent import get_hub as get_gevent_hub
    from gevent.event import Event as GeventPEvent

    try:
        from gevent._hub_local import get_hub_if_exists as current_gevent_hub
    except ImportError:
        current_gevent_hub = get_gevent_hub

    class GeventEvent(GreenEvent):
        __slots__ = (
            "__is_unset",
            "__hub",
            "__event",
        )

        @staticmethod
        def __new__(cls, /):
            self = super(GeventEvent, cls).__new__(cls)

            self.__is_unset = [True]

            self.__hub = get_gevent_hub()
            self.__event = None

            return self

        @classmethod
        def __init_subclass__(cls, /, **kwargs):
            raise TypeError(
                "type 'GeventEvent' is not an acceptable base type",
            )

        def __reduce__(self, /):
            raise TypeError(f"cannot reduce {self!r}")

        def __bool__(self, /):
            return not self.__is_unset

        def wait(self, /, timeout=None):
            success = True

            if self.__is_unset:
                self.__event = GeventPEvent()

                try:
                    hub = self.__hub

                    if not hasattr(hub, "_aiologic_watcher_count"):
                        hub._aiologic_watcher_count = 0
                        hub._aiologic_watcher = hub.loop.async_()

                        # suppress LoopExit
                        hub._aiologic_watcher.start(lambda: None)

                    hub._aiologic_watcher_count += 1

                    try:
                        if timeout is None:
                            success = self.__event.wait()
                        elif timeout > 0:
                            success = self.__event.wait(timeout)
                        else:
                            success = self.__event.wait(0)
                    finally:
                        hub._aiologic_watcher_count -= 1

                        if not hub._aiologic_watcher_count:
                            hub._aiologic_watcher.close()

                            del hub._aiologic_watcher
                            del hub._aiologic_watcher_count
                except BaseException:
                    if is_unset := self.__is_unset:
                        try:
                            is_unset.pop()
                        except IndexError:
                            pass

                    raise
                finally:
                    self.__event = None
            else:
                green_checkpoint()

            return success

        def __set(self, /):
            if (event := self.__event) is not None:
                event.set()

        def set(self, /):
            success = True

            if is_unset := self.__is_unset:
                try:
                    is_unset.pop()
                except IndexError:
                    success = False
                else:
                    hub = current_gevent_hub()

                    if hub is self.__hub:
                        self.__set()
                    else:
                        if (loop := self.__hub.loop) is not None:
                            try:
                                loop.run_callback_threadsafe(self.__set)
                            except ValueError:  # event loop is destroyed
                                pass
            else:
                success = False

            return success

        def is_set(self, /):
            return not self.__is_unset

    return GeventEvent


class ThreadingEvent(GreenEvent):
    __slots__ = ()

    @staticmethod
    def __new__(cls, /):
        try:
            cls = get_threading_event_class()
        except ImportError:
            raise NotImplementedError
        else:
            self = cls.__new__(cls)

        return self


class EventletEvent(GreenEvent):
    __slots__ = ()

    @staticmethod
    def __new__(cls, /):
        try:
            cls = get_eventlet_event_class()
        except ImportError:
            raise NotImplementedError
        else:
            self = cls.__new__(cls)

        return self


class GeventEvent(GreenEvent):
    __slots__ = ()

    @staticmethod
    def __new__(cls, /):
        try:
            cls = get_gevent_event_class()
        except ImportError:
            raise NotImplementedError
        else:
            self = cls.__new__(cls)

        return self


class AsyncEvent(ABC):
    __slots__ = ()

    @staticmethod
    def __new__(cls, /):
        if cls is AsyncEvent:
            library = current_async_library()

            if library == "asyncio":
                self = AsyncioEvent.__new__(AsyncioEvent)
            elif library == "trio":
                self = TrioEvent.__new__(TrioEvent)
            else:
                raise RuntimeError(f"unsupported async library {library!r}")
        else:
            self = super(AsyncEvent, cls).__new__(cls)

        return self

    @abstractmethod
    def __bool__(self, /):
        return self.is_set()

    @abstractmethod
    def __await__(self, /):
        raise NotImplementedError

    @abstractmethod
    def set(self, /):
        raise NotImplementedError

    @abstractmethod
    def is_set(self, /):
        return bool(self)


def get_asyncio_event_class():
    global AsyncioEvent

    from asyncio import get_running_loop as get_running_asyncio_loop

    class AsyncioEvent(AsyncEvent):
        __slots__ = (
            "__is_unset",
            "__loop",
            "__future",
        )

        @staticmethod
        def __new__(cls, /):
            self = super(AsyncioEvent, cls).__new__(cls)

            self.__is_unset = [True]

            self.__loop = get_running_asyncio_loop()
            self.__future = None

            return self

        @classmethod
        def __init_subclass__(cls, /, **kwargs):
            raise TypeError(
                "type 'AsyncioEvent' is not an acceptable base type",
            )

        def __reduce__(self, /):
            raise TypeError(f"cannot reduce {self!r}")

        def __bool__(self, /):
            return not self.__is_unset

        def __await__(self, /):
            if self.__is_unset:
                self.__future = self.__loop.create_future()

                try:
                    yield from self.__future.__await__()
                except BaseException:
                    if is_unset := self.__is_unset:
                        try:
                            is_unset.pop()
                        except IndexError:
                            pass

                    raise
                finally:
                    self.__future = None
            else:
                yield from checkpoint().__await__()

            return True

        def __set(self, /):
            if (future := self.__future) is not None:
                future.set_result(True)

        def set(self, /):
            success = True

            if is_unset := self.__is_unset:
                try:
                    is_unset.pop()
                except IndexError:
                    success = False
                else:
                    try:
                        loop = get_running_asyncio_loop()
                    except RuntimeError:  # no running event loop
                        loop = None

                    if loop is self.__loop:
                        self.__set()
                    else:
                        try:
                            self.__loop.call_soon_threadsafe(self.__set)
                        except RuntimeError:  # event loop is closed
                            pass
            else:
                success = False

            return success

        def is_set(self, /):
            return not self.__is_unset

    return AsyncioEvent


def get_trio_event_class():
    global TrioEvent

    from trio import RunFinishedError
    from trio.lowlevel import (
        Abort,
        reschedule as reschedule_trio_task,
        current_task as current_trio_task,
        current_trio_token,
        wait_task_rescheduled as wait_trio_task_rescheduled,
    )

    class TrioEvent(AsyncEvent):
        __slots__ = (
            "__is_unset",
            "__token",
            "__task",
        )

        @staticmethod
        def __new__(cls, /):
            self = super(TrioEvent, cls).__new__(cls)

            self.__is_unset = [True]

            self.__token = current_trio_token()
            self.__task = None

            return self

        @classmethod
        def __init_subclass__(cls, /, **kwargs):
            raise TypeError("type 'TrioEvent' is not an acceptable base type")

        def __reduce__(self, /):
            raise TypeError(f"cannot reduce {self!r}")

        def __bool__(self, /):
            return not self.__is_unset

        def __await__(self, /):
            if self.__is_unset:
                self.__task = current_trio_task()

                yield from wait_trio_task_rescheduled(self.__abort).__await__()

                self.__task = None
            else:
                yield from checkpoint().__await__()

            return True

        def __abort(self, /, raise_cancel):
            self.__task = None

            if is_unset := self.__is_unset:
                try:
                    is_unset.pop()
                except IndexError:
                    pass

            return Abort.SUCCEEDED

        def __set(self, /):
            if (task := self.__task) is not None:
                reschedule_trio_task(task)

        def set(self, /):
            success = True

            if is_unset := self.__is_unset:
                try:
                    is_unset.pop()
                except IndexError:
                    success = False
                else:
                    try:
                        token = current_trio_token()
                    except RuntimeError:  # no called trio.run
                        token = None

                    if token is self.__token:
                        self.__set()
                    else:
                        try:
                            self.__token.run_sync_soon(self.__set)
                        except RunFinishedError:
                            pass
            else:
                success = False

            return success

        def is_set(self, /):
            return not self.__is_unset

    return TrioEvent


class AsyncioEvent(AsyncEvent):
    __slots__ = ()

    @staticmethod
    def __new__(cls, /):
        try:
            cls = get_asyncio_event_class()
        except ImportError:
            raise NotImplementedError
        else:
            self = cls.__new__(cls)

        return self


class TrioEvent(AsyncEvent):
    __slots__ = ()

    @staticmethod
    def __new__(cls, /):
        try:
            cls = get_trio_event_class()
        except ImportError:
            raise NotImplementedError
        else:
            self = cls.__new__(cls)

        return self
