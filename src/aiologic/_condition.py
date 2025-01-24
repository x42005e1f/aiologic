#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys
import time
import types

from collections import deque
from itertools import count

from ._lock import RLock
from .lowlevel import MISSING, AsyncEvent, GreenEvent, repeat_if_cancelled


class Condition:
    __slots__ = (
        "__timer",
        "__waiters",
        "__weakref__",
        "lock",
    )

    def __new__(cls, /, lock=MISSING):
        self = super().__new__(cls)

        self.__waiters = deque()
        self.__timer = count().__next__

        if lock is MISSING:
            self.lock = RLock()
        elif isinstance(lock, Condition):
            self.lock = lock.lock
        else:
            self.lock = lock

        return self

    def __getnewargs__(self, /):
        return (self.lock,)

    def __repr__(self, /):
        return f"Condition({self.lock!r})"

    def __bool__(self, /):
        if (lock := self.lock) is not None:
            value = bool(lock)
        else:
            value = True

        return value

    async def __aenter__(self, /):
        if (lock := self.lock) is not None:
            value = await lock.__aenter__()
        else:
            value = self

        return value

    async def __aexit__(self, /, exc_type, exc_value, traceback):
        if (lock := self.lock) is not None:
            value = await lock.__aexit__(exc_type, exc_value, traceback)
        else:
            value = None

        return value

    def __enter__(self, /):
        if (lock := self.lock) is not None:
            value = lock.__enter__()
        else:
            value = self

        return value

    def __exit__(self, /, exc_type, exc_value, traceback):
        if (lock := self.lock) is not None:
            value = lock.__exit__(exc_type, exc_value, traceback)
        else:
            value = None

        return value

    def __await__(self, /):
        lock = self.lock
        waiters = self.__waiters
        waiters.append(
            token := (
                event := AsyncEvent(),
                self.__timer(),
            )
        )

        success = False

        try:
            if lock is not None:
                if hasattr(lock, "__aexit__"):
                    state = yield from self._async_release_save().__await__()
                else:
                    state = self._green_release_save()

            try:
                success = yield from event.__await__()
            finally:
                if lock is not None:
                    if hasattr(lock, "__aenter__"):
                        yield from self._async_acquire_restore(
                            state,
                        ).__await__()
                    else:
                        self._green_acquire_restore(state)
        finally:
            if not success:
                if event.cancel():
                    try:
                        waiters.remove(token)
                    except ValueError:
                        pass
                else:
                    self.notify()

        return success

    def wait(self, /, timeout=None):
        lock = self.lock
        waiters = self.__waiters
        waiters.append(
            token := (
                event := GreenEvent(),
                self.__timer(),
            )
        )

        success = False

        try:
            if lock is not None:
                state = self._green_release_save()

            try:
                success = event.wait(timeout)
            finally:
                if lock is not None:
                    self._green_acquire_restore(state)
        finally:
            if not success:
                if event.cancel():
                    try:
                        waiters.remove(token)
                    except ValueError:
                        pass
                else:
                    self.notify()

        return success

    def wait_for(self, /, predicate, timeout=None):
        success = False
        deadline = None

        while not predicate():
            if timeout is not None:
                if deadline is None:
                    deadline = time.monotonic() + timeout
                else:
                    timeout = deadline - time.monotonic()

                    if timeout <= 0:
                        break

            self.wait(timeout)
        else:
            success = True

        return success

    def notify(self, /, count=1, *, deadline=None):
        waiters = self.__waiters

        notified = 0

        while waiters and notified != count:
            try:
                token = waiters[0]
            except IndexError:
                break
            else:
                event, time = token

                if deadline is None:
                    deadline = self.__timer()

                if time <= deadline:
                    if event.set():
                        notified += 1

                    try:
                        waiters.remove(token)
                    except ValueError:
                        pass
                else:
                    break

        return notified

    def notify_all(self, /, *, deadline=None):
        waiters = self.__waiters

        notified = 0

        while waiters:
            try:
                token = waiters[0]
            except IndexError:
                break
            else:
                event, time = token

                if deadline is None:
                    deadline = self.__timer()

                if time <= deadline:
                    if event.set():
                        notified += 1

                    try:
                        waiters.remove(token)
                    except ValueError:
                        pass
                else:
                    break

        return notified

    async def _async_release_save(self, /):
        lock = self.lock

        if (func := getattr(lock, "_async_release_save", None)) is not None:
            state = func()
        else:
            state = await lock.__aexit__(None, None, None)

        return state

    def _green_release_save(self, /):
        lock = self.lock

        if (func := getattr(lock, "_green_release_save", None)) is not None:
            state = func()
        elif (func := getattr(lock, "_release_save", None)) is not None:
            state = func()
        else:
            state = lock.__exit__(None, None, None)

        return state

    async def _async_acquire_restore(self, /, state):
        lock = self.lock

        if (func := getattr(lock, "_async_acquire_restore", None)) is not None:
            await func(state)
        else:
            await repeat_if_cancelled(lock.__aenter__)

    def _green_acquire_restore(self, /, state):
        lock = self.lock

        if (func := getattr(lock, "_green_acquire_restore", None)) is not None:
            func(state)
        elif (func := getattr(lock, "_acquire_restore", None)) is not None:
            func(state)
        else:
            lock.__enter__()

    @property
    def waiting(self, /):
        return len(self.__waiters)

    if sys.version_info >= (3, 9):
        __class_getitem__ = classmethod(types.GenericAlias)
