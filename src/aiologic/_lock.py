#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from collections import deque

from .lowlevel import (
    AsyncEvent,
    GreenEvent,
    async_checkpoint,
    current_async_task_ident,
    current_green_task_ident,
    green_checkpoint,
)


class PLock:
    __slots__ = (
        "__unlocked",
        "__waiters",
        "__weakref__",
    )

    def __new__(cls, /):
        self = super().__new__(cls)

        self.__waiters = deque()
        self.__unlocked = [True]

        return self

    def __repr__(self, /):
        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        return f"{cls_repr}()"

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
                    if self.__acquire_nowait():
                        event.set()

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
                            self.__release()

            if not rescheduled:
                try:
                    await async_checkpoint()
                except BaseException:
                    self.__release()
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
                        event.set()

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
                            self.__release()

            if not rescheduled:
                try:
                    green_checkpoint()
                except BaseException:
                    self.__release()
                    raise

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


class BLock(PLock):
    __slots__ = ("__locked",)

    def __new__(cls, /):
        self = super().__new__(cls)

        self.__locked = []

        return self

    async def async_acquire(self, /, *, blocking=True):
        success = await super().async_acquire(blocking=blocking)

        if success:
            self.__locked.append(True)

        return success

    def green_acquire(self, /, *, blocking=True, timeout=None):
        success = super().green_acquire(blocking=blocking, timeout=timeout)

        if success:
            self.__locked.append(True)

        return success

    def async_release(self, /):
        try:
            self.__locked.pop()
        except IndexError:
            success = False
        else:
            success = True

        if not success:
            msg = "release unlocked lock"
            raise RuntimeError(msg)

        super().async_release()

    def green_release(self, /):
        try:
            self.__locked.pop()
        except IndexError:
            success = False
        else:
            success = True

        if not success:
            msg = "release unlocked lock"
            raise RuntimeError(msg)

        super().green_release()


class Lock(PLock):
    __slots__ = ("owner",)

    def __new__(cls, /):
        self = super().__new__(cls)

        self.owner = None

        return self

    async def async_acquire(self, /, *, blocking=True):
        task = current_async_task_ident()

        if self.owner == task:
            msg = "the current task is already holding this lock"
            raise RuntimeError(msg)

        success = await super().async_acquire(blocking=blocking)

        if success:
            self.owner = task

        return success

    def green_acquire(self, /, *, blocking=True, timeout=None):
        task = current_green_task_ident()

        if self.owner == task:
            msg = "the current task is already holding this lock"
            raise RuntimeError(msg)

        success = super().green_acquire(blocking=blocking, timeout=timeout)

        if success:
            self.owner = task

        return success

    def async_release(self, /):
        if self.owner is None:
            msg = "release unlocked lock"
            raise RuntimeError(msg)

        task = current_async_task_ident()

        if self.owner != task:
            msg = "the current task is not holding this lock"
            raise RuntimeError(msg)

        self.owner = None

        super().async_release()

    def green_release(self, /):
        if self.owner is None:
            msg = "release unlocked lock"
            raise RuntimeError(msg)

        task = current_green_task_ident()

        if self.owner != task:
            msg = "the current task is not holding this lock"
            raise RuntimeError(msg)

        self.owner = None

        super().green_release()


class RLock(PLock):
    __slots__ = (
        "level",
        "owner",
    )

    def __new__(cls, /):
        self = super().__new__(cls)

        self.owner = None
        self.level = 0

        return self

    async def async_acquire(self, /, *, blocking=True):
        task = current_async_task_ident()

        if self.owner != task:
            success = await super().async_acquire(blocking=blocking)

            if success:
                self.owner = task
                self.level += 1
        else:
            await async_checkpoint()

            self.level += 1

            success = True

        return success

    def green_acquire(self, /, *, blocking=True, timeout=None):
        task = current_green_task_ident()

        if self.owner != task:
            success = super().green_acquire(blocking=blocking, timeout=timeout)

            if success:
                self.owner = task
                self.level += 1
        else:
            green_checkpoint()

            self.level += 1

            success = True

        return success

    def async_release(self, /):
        if self.owner is None:
            msg = "release unlocked lock"
            raise RuntimeError(msg)

        task = current_async_task_ident()

        if self.owner != task:
            msg = "the current task is not holding this lock"
            raise RuntimeError(msg)

        self.level -= 1

        if not self.level:
            self.owner = None

            super().async_release()

    def green_release(self, /):
        if self.owner is None:
            msg = "release unlocked lock"
            raise RuntimeError(msg)

        task = current_green_task_ident()

        if self.owner != task:
            msg = "the current task is not holding this lock"
            raise RuntimeError(msg)

        self.level -= 1

        if not self.level:
            self.owner = None

            super().green_release()

    def _async_release_save(self, /):
        if self.owner is None:
            msg = "release unlocked lock"
            raise RuntimeError(msg)

        task = current_async_task_ident()

        if self.owner != task:
            msg = "the current task is not holding this lock"
            raise RuntimeError(msg)

        state = self.owner, self.level

        self.level = 0
        self.owner = None

        super().async_release()

        return state

    def _green_release_save(self, /):
        if self.owner is None:
            msg = "release unlocked lock"
            raise RuntimeError(msg)

        task = current_green_task_ident()

        if self.owner != task:
            msg = "the current task is not holding this lock"
            raise RuntimeError(msg)

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
