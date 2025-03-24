#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import platform

from collections import deque

from .lowlevel import (
    AsyncEvent,
    GreenEvent,
    async_checkpoint,
    green_checkpoint,
)

try:
    from sys import _is_gil_enabled
except ImportError:

    def _is_gil_enabled():
        return True


PYTHON_IMPLEMENTATION = platform.python_implementation()

# bytearray is cheaper than list in memory, but slower on PyPy, so we only use
# it on CPython; but in free-threaded mode, bytearray is not thread-safe, may
# cause SIGSEGV (3.13.0rc1)

USE_BYTEARRAY = PYTHON_IMPLEMENTATION == "CPython" and _is_gil_enabled()


class Semaphore:
    __slots__ = (
        "__unlocked",
        "__waiters",
        "__weakref__",
        "initial_value",
    )

    def __new__(cls, /, initial_value=None, max_value=None):
        if cls is Semaphore and max_value is not None:
            self = BoundedSemaphore.__new__(
                BoundedSemaphore,
                initial_value,
                max_value,
            )
        else:
            self = super().__new__(cls)

            if initial_value is not None:
                if initial_value < 0:
                    msg = "initial_value must be >= 0"
                    raise ValueError(msg)

                self.initial_value = initial_value
            elif max_value is not None:
                if max_value < 0:
                    msg = "max_value must be >= 0"
                    raise ValueError(msg)

                self.initial_value = max_value
            else:
                self.initial_value = 1

            self.__waiters = deque()

            if USE_BYTEARRAY:
                self.__unlocked = bytearray(self.initial_value)
            else:
                self.__unlocked = [None] * self.initial_value

        return self

    def __getnewargs__(self, /):
        if (initial_value := self.initial_value) != 1:
            args = (initial_value,)
        else:
            args = ()

        return args

    def __repr__(self, /):
        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        return f"{cls_repr}({self.initial_value!r})"

    async def __aenter__(self, /):
        await self.async_acquire()

        return self

    async def __aexit__(self, /, exc_type, exc_value, traceback):
        self.async_release()

    def __enter__(self, /):
        self.green_acquire()

        return self

    def __exit__(self, /, exc_type, exc_value, traceback):
        self.green_release()

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

    async def async_acquire(self, /, *, blocking=True):
        waiters = self.__waiters  # abnormal speedup on PyPy3
        success = self.__acquire_nowait()

        if blocking:
            rescheduled = False

            if not success:
                waiters.append(event := AsyncEvent())

                try:
                    if self.__acquire_nowait():
                        if not event.set():
                            self.release()

                    success = await event
                    rescheduled = True
                finally:
                    if not success:
                        if event.cancelled():
                            try:
                                waiters.remove(event)
                            except ValueError:
                                pass
                        else:
                            self.release()

            if not rescheduled:
                try:
                    await async_checkpoint()
                except BaseException:
                    self.release()
                    raise

        return success

    def green_acquire(self, /, *, blocking=True, timeout=None):
        waiters = self.__waiters  # abnormal speedup on PyPy3
        success = self.__acquire_nowait()

        if blocking:
            rescheduled = False

            if not success:
                waiters.append(event := GreenEvent())

                try:
                    if self.__acquire_nowait():
                        if not event.set():
                            self.release()

                    success = event.wait(timeout)
                    rescheduled = True
                finally:
                    if not success:
                        if event.cancelled():
                            try:
                                waiters.remove(event)
                            except ValueError:
                                pass
                        else:
                            self.release()

            if not rescheduled:
                try:
                    green_checkpoint()
                except BaseException:
                    self.release()
                    raise

        return success

    def release(self, /, count=1):
        waiters = self.__waiters
        unlocked = self.__unlocked

        while True:
            if waiters:
                if not count:
                    if self.__acquire_nowait():
                        count = 1
                    else:
                        break

                try:
                    event = waiters[0]
                except IndexError:
                    pass
                else:
                    if event.set():
                        count -= 1

                    try:
                        waiters.remove(event)
                    except ValueError:
                        pass

                    if count or unlocked:
                        continue
                    else:
                        break

            if count == 1:
                if USE_BYTEARRAY:
                    unlocked.append(0)
                else:
                    unlocked.append(None)
            elif count > 1:
                if USE_BYTEARRAY:
                    unlocked.extend(b"\x00" * count)
                else:
                    unlocked.extend([None] * count)
            else:
                break

            if waiters:
                count = 0
            else:
                break

    async_release = release
    green_release = release

    @property
    def waiting(self, /):
        return len(self.__waiters)

    @property
    def value(self, /):
        return len(self.__unlocked)


class BoundedSemaphore(Semaphore):
    __slots__ = (
        "__locked",
        "max_value",
    )

    def __new__(cls, /, initial_value=None, max_value=None):
        self = super().__new__(cls, initial_value, max_value)

        if max_value is not None:
            if max_value < self.initial_value:
                msg = "max_value must be >= initial_value"
                raise ValueError(msg)

            self.max_value = max_value
        else:
            self.max_value = self.initial_value

        if USE_BYTEARRAY:
            self.__locked = bytearray(self.max_value - self.initial_value)
        else:
            self.__locked = [None] * (self.max_value - self.initial_value)

        return self

    def __getnewargs__(self, /):
        initial_value = self.initial_value
        max_value = self.max_value

        if initial_value != max_value:
            args = (initial_value, max_value)
        elif initial_value != 1:
            args = (initial_value,)
        else:
            args = ()

        return args

    def __repr__(self, /):
        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        initial_value = self.initial_value
        max_value = self.max_value

        if initial_value != max_value:
            args_repr = f"{initial_value!r}, max_value={max_value!r}"
        else:
            args_repr = f"{initial_value!r}"

        return f"{cls_repr}({args_repr})"

    async def async_acquire(self, /, *, blocking=True):
        success = await super().async_acquire(blocking=blocking)

        if success:
            if USE_BYTEARRAY:
                self.__locked.append(0)
            else:
                self.__locked.append(None)

        return success

    def green_acquire(self, /, *, blocking=True, timeout=None):
        success = super().green_acquire(blocking=blocking, timeout=timeout)

        if success:
            if USE_BYTEARRAY:
                self.__locked.append(0)
            else:
                self.__locked.append(None)

        return success

    def release(self, /, count=1):
        if count == 1:
            try:
                self.__locked.pop()
            except IndexError:
                success = False
            else:
                success = True

            if not success:
                msg = "semaphore released too many times"
                raise RuntimeError(msg)
        elif count:
            msg = "count must be 0 or 1"
            raise ValueError(msg)

        super().release(count)

    async_release = release
    green_release = release
