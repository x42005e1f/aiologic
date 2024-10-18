#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

__all__ = (
    "QueueEmpty",
    "QueueFull",
    "ExclusiveQueue",
    "Queue",
    "LifoQueue",
    "PriorityQueue",
)

from collections import deque

from aiologic.lowlevel import (
    AsyncEvent,
    GreenEvent,
    checkpoint,
    green_checkpoint,
)

from .locks import Semaphore
from .lowlevel import MISSING

try:
    from _heapq import heappop, heappush
except ImportError:
    from heapq import heappop, heappush

    is_heapq_atomic = False
else:
    try:
        from sys import _is_gil_enabled
    except ImportError:
        is_heapq_atomic = True
    else:
        is_heapq_atomic = _is_gil_enabled()


class QueueEmpty(Exception):
    pass


class QueueFull(Exception):
    pass


class ExclusiveQueue:
    __slots__ = (
        "__weakref__",
        "__waiters",
        "__get_waiters",
        "__put_waiters",
        "__unlocked",
        "_data",
        "maxsize",
    )

    @staticmethod
    def __new__(cls, items=MISSING, /, maxsize=None):
        if maxsize is None:
            if isinstance(items, int):
                items, maxsize = MISSING, items
            else:
                maxsize = 0

        self = super(ExclusiveQueue, cls).__new__(cls)

        self._data = self._make(items)

        self.__waiters = deque()
        self.__get_waiters = deque()
        self.__put_waiters = deque()
        self.__unlocked = [True]

        self.maxsize = maxsize

        return self

    def __getnewargs__(self, /):
        if (maxsize := self.maxsize) != 0:
            args = (list(self._data), maxsize)
        else:
            args = (list(self._data),)

        return args

    def __repr__(self, /):
        if (maxsize := self.maxsize) != 0:
            args_repr = f"{repr(list(self._data))}, maxsize={maxsize!r}"
        else:
            args_repr = repr(list(self._data))

        return f"{self.__class__.__name__}({args_repr})"

    def __bool__(self, /):
        return bool(self._data)

    def __len__(self, /):
        return len(self._data)

    def __acquire_nowait(self, /):
        if unlocked := self.__unlocked:
            try:
                unlocked.pop()
            except IndexError:
                success = False
            else:
                success = True
        else:
            success = False

        return success

    def __release(self, /):
        data = self._data
        maxsize = self.maxsize

        waiters = self.__waiters
        put_waiters = self.__put_waiters
        get_waiters = self.__get_waiters
        unlocked = self.__unlocked

        while True:
            size = len(data)

            if not size:
                actual_waiters = put_waiters
            elif size >= maxsize > 0:
                actual_waiters = get_waiters
            else:
                actual_waiters = waiters

            if actual_waiters:
                try:
                    event = actual_waiters.popleft()
                except IndexError:
                    pass
                else:
                    if event.set():
                        break
                    else:
                        continue

            unlocked.append(True)

            if actual_waiters:
                if self.__acquire_nowait():
                    continue
                else:
                    break
            else:
                break

    async def async_put(self, /, item, *, blocking=True):
        data = self._data
        maxsize = self.maxsize

        waiters = self.__waiters
        put_waiters = self.__put_waiters

        if maxsize <= 0:
            success = self.__acquire_nowait()
        elif len(data) < maxsize:
            success = self.__acquire_nowait()

            if success and len(data) == maxsize:
                self.__release()

                success = False
        else:
            success = False

        if blocking:
            rescheduled = False

            if not success:
                event = AsyncEvent()

                waiters.append(event)
                put_waiters.append(event)

                try:
                    if maxsize <= 0:
                        success = self.__acquire_nowait()
                    elif len(data) < maxsize:
                        success = self.__acquire_nowait()

                        if success and len(data) == maxsize:
                            self.__release()

                            success = False
                    else:
                        success = False

                    if not success:
                        success = await event
                        rescheduled = True
                finally:
                    if success or event.set():
                        try:
                            put_waiters.remove(event)
                        except ValueError:
                            pass

                        try:
                            waiters.remove(event)
                        except ValueError:
                            pass
                    else:
                        self.__release()

            if not rescheduled:
                await checkpoint()

        if not success:
            raise QueueFull

        try:
            self._put(item)
        finally:
            self.__release()

    def green_put(self, /, item, *, blocking=True, timeout=None):
        data = self._data
        maxsize = self.maxsize

        waiters = self.__waiters
        put_waiters = self.__put_waiters

        if maxsize <= 0:
            success = self.__acquire_nowait()
        elif len(data) < maxsize:
            success = self.__acquire_nowait()

            if success and len(data) == maxsize:
                self.__release()

                success = False
        else:
            success = False

        if blocking:
            rescheduled = False

            if not success:
                event = GreenEvent()

                waiters.append(event)
                put_waiters.append(event)

                try:
                    if maxsize <= 0:
                        success = self.__acquire_nowait()
                    elif len(data) < maxsize:
                        success = self.__acquire_nowait()

                        if success and len(data) == maxsize:
                            self.__release()

                            success = False
                    else:
                        success = False

                    if not success:
                        success = event.wait(timeout)
                        rescheduled = True
                finally:
                    if success or event.set():
                        try:
                            put_waiters.remove(event)
                        except ValueError:
                            pass

                        try:
                            waiters.remove(event)
                        except ValueError:
                            pass
                    else:
                        self.__release()

            if not rescheduled:
                green_checkpoint()

        if not success:
            raise QueueFull

        try:
            self._put(item)
        finally:
            self.__release()

    async def async_get(self, /, *, blocking=True):
        data = self._data

        waiters = self.__waiters
        get_waiters = self.__get_waiters

        if data:
            success = self.__acquire_nowait()

            if success and not data:
                self.__release()

                success = False
        else:
            success = False

        if blocking:
            rescheduled = False

            if not success:
                event = AsyncEvent()

                waiters.append(event)
                get_waiters.append(event)

                try:
                    if data:
                        success = self.__acquire_nowait()

                        if success and not data:
                            self.__release()

                            success = False
                    else:
                        success = False

                    if not success:
                        success = await event
                        rescheduled = True
                finally:
                    if success or event.set():
                        try:
                            get_waiters.remove(event)
                        except ValueError:
                            pass

                        try:
                            waiters.remove(event)
                        except ValueError:
                            pass
                    else:
                        self.__release()

            if not rescheduled:
                await checkpoint()

        if not success:
            raise QueueEmpty

        try:
            item = self._get()
        finally:
            self.__release()

        return item

    def green_get(self, /, *, blocking=True, timeout=None):
        data = self._data

        waiters = self.__waiters
        get_waiters = self.__get_waiters

        if data:
            success = self.__acquire_nowait()

            if success and not data:
                self.__release()

                success = False
        else:
            success = False

        if blocking:
            rescheduled = False

            if not success:
                event = GreenEvent()

                waiters.append(event)
                get_waiters.append(event)

                try:
                    if data:
                        success = self.__acquire_nowait()

                        if success and not data:
                            self.__release()

                            success = False
                    else:
                        success = False

                    if not success:
                        success = event.wait(timeout)
                        rescheduled = True
                finally:
                    if success or event.set():
                        try:
                            get_waiters.remove(event)
                        except ValueError:
                            pass

                        try:
                            waiters.remove(event)
                        except ValueError:
                            pass
                    else:
                        self.__release()

            if not rescheduled:
                green_checkpoint()

        if not success:
            raise QueueEmpty

        try:
            item = self._get()
        finally:
            self.__release()

        return item

    def _make(self, /, items=MISSING):
        if items is not MISSING:
            data = deque(items)
        else:
            data = deque()

        return data

    def _put(self, /, item):
        self._data.append(item)

    def _get(self, /):
        return self._data.popleft()

    @property
    def waiting(self, /):
        return len(self.__waiters)

    @property
    def putting(self, /):
        return len(self.__put_waiters)

    @property
    def getting(self, /):
        return len(self.__get_waiters)


class Queue:
    __slots__ = (
        "__weakref__",
        "__get_lock",
        "__put_lock",
        "_data",
        "maxsize",
    )

    @staticmethod
    def __new__(cls, items=MISSING, /, maxsize=None):
        if maxsize is None:
            if isinstance(items, int):
                items, maxsize = MISSING, items
            else:
                maxsize = 0

        self = super(Queue, cls).__new__(cls)

        self._data = data = self._make(items)

        self.__get_lock = Semaphore(len(data))

        if maxsize > 0:
            self.__put_lock = Semaphore(maxsize - len(data))
        else:
            self.__put_lock = None

        self.maxsize = maxsize

        return self

    def __getnewargs__(self, /):
        if (maxsize := self.maxsize) != 0:
            args = (list(self._data), maxsize)
        else:
            args = (list(self._data),)

        return args

    def __repr__(self, /):
        if (maxsize := self.maxsize) != 0:
            args_repr = f"{repr(list(self._data))}, maxsize={maxsize!r}"
        else:
            args_repr = repr(list(self._data))

        return f"{self.__class__.__name__}({args_repr})"

    def __bool__(self, /):
        return bool(self._data)

    def __len__(self, /):
        return len(self._data)

    async def async_put(self, /, item, *, blocking=True):
        if (put_lock := self.__put_lock) is not None:
            success = await put_lock.async_acquire(blocking=blocking)

            if not success:
                raise QueueFull

        self._put(item)

        if (get_lock := self.__get_lock) is not None:
            get_lock.async_release()

    def green_put(self, /, item, *, blocking=True, timeout=None):
        if (put_lock := self.__put_lock) is not None:
            success = put_lock.green_acquire(
                blocking=blocking,
                timeout=timeout,
            )

            if not success:
                raise QueueFull

        self._put(item)

        if (get_lock := self.__get_lock) is not None:
            get_lock.green_release()

    async def async_get(self, /, *, blocking=True):
        if (get_lock := self.__get_lock) is not None:
            success = await get_lock.async_acquire(blocking=blocking)

            if not success:
                raise QueueEmpty

        item = self._get()

        if (put_lock := self.__put_lock) is not None:
            put_lock.async_release()

        return item

    def green_get(self, /, *, blocking=True, timeout=None):
        if (get_lock := self.__get_lock) is not None:
            success = get_lock.green_acquire(
                blocking=blocking,
                timeout=timeout,
            )

            if not success:
                raise QueueEmpty

        item = self._get()

        if (put_lock := self.__put_lock) is not None:
            put_lock.green_release()

        return item

    def _make(self, /, items=MISSING):
        if items is not MISSING:
            data = deque(items)
        else:
            data = deque()

        return data

    def _put(self, /, item):
        self._data.append(item)

    def _get(self, /):
        return self._data.popleft()

    @property
    def waiting(self, /):
        return abs(self.putting - self.getting)

    @property
    def putting(self, /):
        if (put_lock := self.__put_lock) is not None:
            value = put_lock.waiting
        else:
            value = 0

        return value

    @property
    def getting(self, /):
        if (get_lock := self.__get_lock) is not None:
            value = get_lock.waiting
        else:
            value = 0

        return value


class LifoQueue(Queue):
    __slots__ = ()

    def _make(self, /, items=MISSING):
        if items is not MISSING:
            data = list(items)
        else:
            data = []

        return data

    def _put(self, /, item):
        self._data.append(item)

    def _get(self, /):
        return self._data.pop()


if is_heapq_atomic:

    class PriorityQueue(Queue):
        __slots__ = ()

        def _make(self, /, items=MISSING):
            if items is not MISSING:
                data = list(items)
            else:
                data = []

            return data

        def _put(self, /, item):
            heappush(self._data, item)

        def _get(self, /):
            return heappop(self._data)

else:

    class PriorityQueue(ExclusiveQueue):
        __slots__ = ()

        def _make(self, /, items=MISSING):
            if items is not MISSING:
                data = list(items)
            else:
                data = []

            return data

        def _put(self, /, item):
            heappush(self._data, item)

        def _get(self, /):
            return heappop(self._data)
