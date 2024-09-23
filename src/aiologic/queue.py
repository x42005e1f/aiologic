#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

__all__ = (
    "QueueEmpty",
    "QueueFull",
    "Queue",
    "LifoQueue",
)

from collections import deque

from .locks import Semaphore
from .lowlevel import MISSING


class QueueEmpty(Exception):
    pass


class QueueFull(Exception):
    pass


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
        self._data.popleft()

    @property
    def waiting(self, /):
        return self.__lock.waiting


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
        self._data.pop()
