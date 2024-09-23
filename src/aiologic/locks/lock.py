#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

__all__ = (
    "PLock",
    "Lock",
    "RLock",
)

from collections import deque

from aiologic.lowlevel import (
    AsyncEvent,
    GreenEvent,
    checkpoint,
    green_checkpoint,
    current_async_task_ident,
    current_green_task_ident,
)


class PLock:
    __slots__ = (
        "__weakref__",
        "__waiters",
        "__unlocked",
    )

    @staticmethod
    def __new__(cls, /):
        self = super(PLock, cls).__new__(cls)

        self.__waiters = deque()
        self.__unlocked = [True]

        return self

    def __repr__(self, /):
        return "PLock()"

    def __bool__(self, /):
        return not self.__unlocked

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
                    success = self.__acquire_nowait()

                    if not success:
                        success = await event
                        rescheduled = True
                finally:
                    if success or event.set():
                        try:
                            waiters.remove(event)
                        except ValueError:
                            pass
                    else:
                        self.__release()

            if not rescheduled:
                await checkpoint()

        return success

    def green_acquire(self, /, *, blocking=True, timeout=None):
        waiters = self.__waiters  # abnormal speedup on PyPy3
        success = self.__acquire_nowait()

        if blocking:
            rescheduled = False

            if not success:
                waiters.append(event := GreenEvent())

                try:
                    success = self.__acquire_nowait()

                    if not success:
                        success = event.wait(timeout)
                        rescheduled = True
                finally:
                    if success or event.set():
                        try:
                            waiters.remove(event)
                        except ValueError:
                            pass
                    else:
                        self.__release()

            if not rescheduled:
                green_checkpoint()

        return success

    def __release(self, /):
        waiters = self.__waiters
        unlocked = self.__unlocked

        while True:
            if waiters:
                try:
                    event = waiters.popleft()
                except IndexError:
                    pass
                else:
                    if event.set():
                        break
                    else:
                        continue

            unlocked.append(True)

            if waiters:
                if self.__acquire_nowait():
                    continue
                else:
                    break
            else:
                break

    async_release = __release
    green_release = __release

    def locked(self, /):
        return not self.__unlocked

    @property
    def waiting(self, /):
        return len(self.__waiters)


class Lock(PLock):
    __slots__ = ("owner",)

    @staticmethod
    def __new__(cls, /):
        self = super(Lock, cls).__new__(cls)

        self.owner = None

        return self

    def __repr__(self, /):
        return "Lock()"

    async def async_acquire(self, /, *, blocking=True):
        task = current_async_task_ident()

        if self.owner == task:
            raise RuntimeError(
                "the current task is already holding this lock",
            )

        success = await super().async_acquire(blocking=blocking)

        if success:
            self.owner = task

        return success

    def green_acquire(self, /, *, blocking=True, timeout=None):
        task = current_green_task_ident()

        if self.owner == task:
            raise RuntimeError(
                "the current task is already holding this lock",
            )

        success = super().green_acquire(blocking=blocking, timeout=timeout)

        if success:
            self.owner = task

        return success

    def async_release(self, /):
        if self.owner is None:
            raise RuntimeError("release unlocked lock")

        task = current_async_task_ident()

        if self.owner != task:
            raise RuntimeError("the current task is not holding this lock")

        self.owner = None

        super().async_release()

    def green_release(self, /):
        if self.owner is None:
            raise RuntimeError("release unlocked lock")

        task = current_green_task_ident()

        if self.owner != task:
            raise RuntimeError("the current task is not holding this lock")

        self.owner = None

        super().green_release()


class RLock(PLock):
    __slots__ = (
        "owner",
        "level",
    )

    @staticmethod
    def __new__(cls, /):
        self = super(RLock, cls).__new__(cls)

        self.owner = None
        self.level = 0

        return self

    def __repr__(self, /):
        return "RLock()"

    async def async_acquire(self, /, *, blocking=True):
        task = current_async_task_ident()

        if self.owner != task:
            success = await super().async_acquire(blocking=blocking)

            if success:
                self.owner = task
        else:
            success = True

        if success:
            self.level += 1

        return success

    def green_acquire(self, /, *, blocking=True, timeout=None):
        task = current_green_task_ident()

        if self.owner != task:
            success = super().green_acquire(blocking=blocking, timeout=timeout)

            if success:
                self.owner = task
        else:
            success = True

        if success:
            self.level += 1

        return success

    def async_release(self, /):
        if self.owner is None:
            raise RuntimeError("release unlocked lock")

        task = current_async_task_ident()

        if self.owner != task:
            raise RuntimeError("the current task is not holding this lock")

        self.level -= 1

        if not self.level:
            self.owner = None

            super().async_release()

    def green_release(self, /):
        if self.owner is None:
            raise RuntimeError("release unlocked lock")

        task = current_green_task_ident()

        if self.owner != task:
            raise RuntimeError("the current task is not holding this lock")

        self.level -= 1

        if not self.level:
            self.owner = None

            super().green_release()

    def _async_release_save(self, /):
        if self.owner is None:
            raise RuntimeError("release unlocked lock")

        task = current_async_task_ident()

        if self.owner != task:
            raise RuntimeError("the current task is not holding this lock")

        state = self.owner, self.level

        self.level = 0
        self.owner = None

        super().async_release()

        return state

    def _green_release_save(self, /):
        if self.owner is None:
            raise RuntimeError("release unlocked lock")

        task = current_green_task_ident()

        if self.owner != task:
            raise RuntimeError("the current task is not holding this lock")

        state = self.owner, self.level

        self.level = 0
        self.owner = None

        super().green_release()

        return state

    async def _async_acquire_restore(self, /, state):
        success = await super().async_acquire()

        if success:
            self.owner, self.level = state

        return success

    def _green_acquire_restore(self, /, state):
        success = super().green_acquire()

        if success:
            self.owner, self.level = state

        return success
