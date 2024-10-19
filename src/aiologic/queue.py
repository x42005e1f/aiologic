#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

__all__ = (
    "QueueEmpty",
    "QueueFull",
    "SimpleQueue",
    "Queue",
    "LifoQueue",
    "PriorityQueue",
)

from heapq import heappop, heappush
from collections import deque

from aiologic.lowlevel import (
    AsyncEvent,
    GreenEvent,
    checkpoint,
    green_checkpoint,
)

from .locks import Semaphore
from .lowlevel import MISSING


class QueueEmpty(Exception):
    pass


class QueueFull(Exception):
    pass


class SimpleQueue:
    __slots__ = (
        "__weakref__",
        "__sem",
        "_data",
    )

    @staticmethod
    def __new__(cls, items=MISSING, /):
        self = super(SimpleQueue, cls).__new__(cls)

        if items is not MISSING:
            self._data = data = deque(items)
        else:
            self._data = data = deque()

        self.__sem = Semaphore(len(data))

        return self

    def __getnewargs__(self, /):
        return (list(self._data),)

    def __repr__(self, /):
        return f"SimpleQueue({list(self._data)!r})"

    def __bool__(self, /):
        return bool(self._data)

    def __len__(self, /):
        return len(self._data)

    def put(self, /, item):
        self._data.append(item)
        self.__sem.release()

    async def async_put(self, /, item, *, blocking=True):
        if blocking:
            await checkpoint()

        self._data.append(item)
        self.__sem.async_release()

    def green_put(self, /, item, *, blocking=True, timeout=None):
        if blocking:
            green_checkpoint()

        self._data.append(item)
        self.__sem.green_release()

    async def async_get(self, /, *, blocking=True):
        success = await self.__sem.async_acquire(blocking=blocking)

        if not success:
            raise QueueEmpty

        return self._data.popleft()

    def green_get(self, /, *, blocking=True, timeout=None):
        success = self.__sem.green_acquire(blocking=blocking, timeout=timeout)

        if not success:
            raise QueueEmpty

        return self._data.popleft()

    @property
    def waiting(self, /):
        return self.__sem.waiting

    @property
    def putting(self, /):
        return 0

    @property
    def getting(self, /):
        return self.__sem.waiting


class Queue:
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

        if items is MISSING:
            items = ()

        self = super(Queue, cls).__new__(cls)

        self._init(items, maxsize)

        self.__waiters = deque()
        self.__get_waiters = deque()
        self.__put_waiters = deque()
        self.__unlocked = [True]

        self.maxsize = maxsize

        return self

    def __getnewargs__(self, /):
        if (maxsize := self.maxsize) != 0:
            args = (self._items(), maxsize)
        else:
            args = (self._items(),)

        return args

    def __repr__(self, /):
        if (maxsize := self.maxsize) != 0:
            args_repr = f"{repr(self._items())}, maxsize={maxsize!r}"
        else:
            args_repr = repr(self._items())

        return f"{self.__class__.__name__}({args_repr})"

    def __bool__(self, /):
        return self._qsize() > 0

    def __len__(self, /):
        return self._qsize()

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
        maxsize = self.maxsize

        waiters = self.__waiters
        put_waiters = self.__put_waiters
        get_waiters = self.__get_waiters
        unlocked = self.__unlocked

        while True:
            size = self._qsize()

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
        maxsize = self.maxsize

        waiters = self.__waiters
        put_waiters = self.__put_waiters

        if maxsize <= 0:
            success = self.__acquire_nowait()
        elif self._qsize() < maxsize:
            success = self.__acquire_nowait()

            if success and self._qsize() >= maxsize:
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
                    elif self._qsize() < maxsize:
                        success = self.__acquire_nowait()

                        if success and self._qsize() >= maxsize:
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
        maxsize = self.maxsize

        waiters = self.__waiters
        put_waiters = self.__put_waiters

        if maxsize <= 0:
            success = self.__acquire_nowait()
        elif self._qsize() < maxsize:
            success = self.__acquire_nowait()

            if success and self._qsize() >= maxsize:
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
                    elif self._qsize() < maxsize:
                        success = self.__acquire_nowait()

                        if success and self._qsize() >= maxsize:
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
        waiters = self.__waiters
        get_waiters = self.__get_waiters

        if self._qsize() > 0:
            success = self.__acquire_nowait()

            if success and self._qsize() <= 0:
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
                    if self._qsize() > 0:
                        success = self.__acquire_nowait()

                        if success and self._qsize() <= 0:
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
        waiters = self.__waiters
        get_waiters = self.__get_waiters

        if self._qsize() > 0:
            success = self.__acquire_nowait()

            if success and self._qsize() <= 0:
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
                    if self._qsize() > 0:
                        success = self.__acquire_nowait()

                        if success and self._qsize() <= 0:
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

    def _init(self, /, items, maxsize):
        self._data = deque(items)

    def _qsize(self, /):
        return len(self._data)

    def _items(self, /):
        return list(self._data)

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


class LifoQueue(Queue):
    __slots__ = ()

    def _init(self, /, items, maxsize):
        self._data = list(items)

    def _put(self, /, item):
        self._data.append(item)

    def _get(self, /):
        return self._data.pop()


class PriorityQueue(Queue):
    __slots__ = ()

    def _init(self, /, items, maxsize):
        self._data = list(items)

    def _put(self, /, item):
        heappush(self._data, item)

    def _get(self, /):
        return heappop(self._data)
