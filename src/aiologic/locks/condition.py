#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

__all__ = ("Condition",)

import time

from itertools import count
from collections import deque

from aiologic.lowlevel import AsyncEvent, GreenEvent, shield

from .lock import RLock
from .limiter import RCapacityLimiter


class Condition:
    __slots__ = (
        "__weakref__",
        "__waiters",
        "__timer",
        "lock",
    )

    @staticmethod
    def __new__(cls, /, lock=None):
        if lock is None:
            lock = RLock()

        self = super(Condition, cls).__new__(cls)

        self.__waiters = deque()
        self.__timer = count().__next__

        self.lock = lock

        return self

    def __getnewargs__(self, /):
        return (self.lock,)

    def __repr__(self, /):
        return f"Condition({self.lock!r})"

    def __bool__(self, /):
        return bool(self.lock)

    async def __aenter__(self, /):
        return await self.lock.__aenter__()

    async def __aexit__(self, /, exc_type, exc_value, traceback):
        return await self.lock.__aexit__(exc_type, exc_value, traceback)

    def __enter__(self, /):
        return self.lock.__enter__()

    def __exit__(self, /, exc_type, exc_value, traceback):
        return self.lock.__exit__(exc_type, exc_value, traceback)

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
            if isinstance(lock, (RLock, RCapacityLimiter)):
                state = lock._async_release_save()
            else:
                yield from lock.__aexit__(None, None, None).__await__()

            try:
                success = yield from event.__await__()
            finally:
                if isinstance(lock, (RLock, RCapacityLimiter)):
                    yield from shield(
                        lock._async_acquire_restore(state),
                    ).__await__()
                else:
                    yield from shield(
                        lock.__aenter__(),
                    ).__await__()
        finally:
            if success or event.set():
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
            if isinstance(lock, (RLock, RCapacityLimiter)):
                state = lock._green_release_save()
            else:
                lock.__exit__(None, None, None)

            try:
                success = event.wait(timeout)
            finally:
                if isinstance(lock, (RLock, RCapacityLimiter)):
                    lock._green_acquire_restore(state)
                else:
                    lock.__enter__()
        finally:
            if success or event.set():
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

        if deadline is None:
            deadline = self.__timer()

        notified = 0

        while waiters and notified != count:
            try:
                token = waiters[0]
            except IndexError:
                break
            else:
                event, time = token

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

        if deadline is None:
            deadline = self.__timer()

        notified = 0

        while waiters:
            try:
                token = waiters[0]
            except IndexError:
                break
            else:
                event, time = token

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

    @property
    def waiting(self, /):
        return len(self.__waiters)
