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

        self.__unlocked = [True]
        self.__waiters = deque()

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
        if self.__unlocked:
            try:
                self.__unlocked.pop()
            except IndexError:
                return False
            else:
                return True

        return False

    async def async_acquire(self, /, *, blocking=True):
        if self.__acquire_nowait():
            if blocking:
                try:
                    await async_checkpoint()
                except BaseException:
                    self._release()
                    raise

            return True

        if not blocking:
            return False

        self.__waiters.append(event := AsyncEvent())

        if self.__acquire_nowait():
            event.set()  # event will be removed on release

        success = False

        try:
            success = await event
        finally:
            if not success:
                if event.cancelled():
                    try:
                        self.__waiters.remove(event)
                    except ValueError:
                        pass
                else:
                    self._release()

        return success

    def green_acquire(self, /, *, blocking=True, timeout=None):
        if self.__acquire_nowait():
            if blocking:
                try:
                    green_checkpoint()
                except BaseException:
                    self._release()
                    raise

            return True

        if not blocking:
            return False

        self.__waiters.append(event := GreenEvent())

        if self.__acquire_nowait():
            event.set()  # event will be removed on release

        success = False

        try:
            success = event.wait(timeout)
        finally:
            if not success:
                if event.cancelled():
                    try:
                        self.__waiters.remove(event)
                    except ValueError:
                        pass
                else:
                    self._release()

        return success

    def _release(self, /):
        waiters = self.__waiters

        while True:
            while waiters:
                try:
                    event = waiters.popleft()
                except IndexError:
                    pass
                else:
                    if event.set():
                        return

            self.__unlocked.append(True)

            if waiters:
                try:
                    self.__unlocked.pop()
                except IndexError:
                    break
            else:
                break

    _async_acquire = async_acquire
    _green_acquire = green_acquire

    async_release = _release
    green_release = _release

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
        success = await self._async_acquire(blocking=blocking)

        if success:
            self.__locked.append(True)

        return success

    def green_acquire(self, /, *, blocking=True, timeout=None):
        success = self._green_acquire(blocking=blocking, timeout=timeout)

        if success:
            self.__locked.append(True)

        return success

    def async_release(self, /):
        try:
            self.__locked.pop()
        except IndexError:
            msg = "release unlocked lock"
            raise RuntimeError(msg) from None

        self._release()

    def green_release(self, /):
        try:
            self.__locked.pop()
        except IndexError:
            msg = "release unlocked lock"
            raise RuntimeError(msg) from None

        self._release()


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

        success = await self._async_acquire(blocking=blocking)

        if success:
            self.owner = task

        return success

    def green_acquire(self, /, *, blocking=True, timeout=None):
        task = current_green_task_ident()

        if self.owner == task:
            msg = "the current task is already holding this lock"
            raise RuntimeError(msg)

        success = self._green_acquire(blocking=blocking, timeout=timeout)

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

        self._release()

    def green_release(self, /):
        if self.owner is None:
            msg = "release unlocked lock"
            raise RuntimeError(msg)

        task = current_green_task_ident()

        if self.owner != task:
            msg = "the current task is not holding this lock"
            raise RuntimeError(msg)

        self.owner = None

        self._release()


class RLock(PLock):
    __slots__ = (
        "level",
        "owner",
    )

    def __new__(cls, /):
        self = super().__new__(cls)

        self.level = 0
        self.owner = None

        return self

    async def async_acquire(self, /, count=1, *, blocking=True):
        task = current_async_task_ident()

        if self.owner == task:
            await async_checkpoint()

            self.level += count

            return True

        success = await self._async_acquire(blocking=blocking)

        if success:
            self.owner = task
            self.level = count

        return success

    def green_acquire(self, /, count=1, *, blocking=True, timeout=None):
        task = current_green_task_ident()

        if self.owner == task:
            green_checkpoint()

            self.level += count

            return True

        success = self._green_acquire(blocking=blocking, timeout=timeout)

        if success:
            self.owner = task
            self.level = count

        return success

    def async_release(self, /, count=1):
        if self.owner is None:
            msg = "release unlocked lock"
            raise RuntimeError(msg)

        task = current_async_task_ident()

        if self.owner != task:
            msg = "the current task is not holding this lock"
            raise RuntimeError(msg)

        if self.level < count:
            msg = "lock released too many times"
            raise RuntimeError(msg)

        self.level -= count

        if not self.level:
            self.owner = None

            self._release()

    def green_release(self, /, count=1):
        if self.owner is None:
            msg = "release unlocked lock"
            raise RuntimeError(msg)

        task = current_green_task_ident()

        if self.owner != task:
            msg = "the current task is not holding this lock"
            raise RuntimeError(msg)

        if self.level < count:
            msg = "lock released too many times"
            raise RuntimeError(msg)

        self.level -= count

        if not self.level:
            self.owner = None

            self._release()

    # Internal methods used by condition variables

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

        self._release()

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

        self._release()

        return state

    async def _async_acquire_restore(self, /, state):
        success = await self._async_acquire()

        if success:
            self.owner, self.level = state

        return success

    def _green_acquire_restore(self, /, state):
        success = self._green_acquire()

        if success:
            self.owner, self.level = state

        return success
