#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys
import time
import types

from collections import defaultdict, deque
from itertools import count

from ._lock import RLock
from .lowlevel import (
    MISSING,
    AsyncEvent,
    GreenEvent,
    current_async_task_ident,
    current_green_task_ident,
    shield,
)


class Condition:
    __slots__ = (
        "__impl",
        "__weakref__",
    )

    def __new__(cls, /, lock=MISSING, timer=MISSING):
        if lock is MISSING:
            lock = RLock()

        if timer is MISSING:
            timer = count().__next__

        if lock is None:
            imp = _BaseCondition
        elif hasattr(lock, "_async_acquire_restore"):
            imp = _RMixedCondition
        elif hasattr(lock, "async_acquire"):
            imp = _MixedCondition
        elif hasattr(lock, "_is_owned"):
            imp = _RSyncCondition
        else:
            imp = _SyncCondition

        if cls is Condition:
            return imp.__new__(imp, lock, timer)

        self = super().__new__(cls)

        self.__impl = imp(lock, timer)

        return self

    def __getnewargs__(self, /):
        return (self.lock,)

    def __repr__(self, /):
        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        return f"{cls_repr}({self.lock!r})"

    def __bool__(self, /):
        return bool(self.__impl)

    async def __aenter__(self, /):
        return await self.__impl.__aenter__()

    def __enter__(self, /):
        return self.__impl.__enter__()

    async def __aexit__(self, /, exc_type, exc_value, traceback):
        return await self.__impl.__aexit__(exc_type, exc_value, traceback)

    def __exit__(self, /, exc_type, exc_value, traceback):
        return self.__impl.__exit__(exc_type, exc_value, traceback)

    def __await__(self, /):
        return (yield from self.__impl.__await__())

    def wait(self, /, timeout=None):
        return self.__impl.wait(timeout)

    async def for_(self, /, predicate):
        while True:
            result = predicate()

            if result:
                return result

            await self

    def wait_for(self, /, predicate, timeout=None):
        deadline = None

        while True:
            result = predicate()

            if result:
                return result

            if timeout is not None:
                if deadline is None:
                    deadline = time.monotonic() + timeout
                else:
                    timeout = deadline - time.monotonic()

                    if timeout < 0:
                        return result

            self.wait(timeout)

    def notify(self, /, count=1, *, deadline=None):
        return self.__impl.notify(count, deadline=deadline)

    def notify_all(self, /, *, deadline=None):
        return self.__impl.notify_all(deadline=deadline)

    @property
    def waiting(self, /):
        return self.__impl.waiting

    if sys.version_info >= (3, 9):
        __class_getitem__ = classmethod(types.GenericAlias)


class _BaseCondition(Condition):
    __slots__ = (
        "_waiters",
        "lock",
        "timer",
    )

    def __new__(cls, /, lock, timer):
        self = object.__new__(cls)

        self._waiters = deque()

        self.lock = lock
        self.timer = timer

        return self

    def __init_subclass__(cls, /, **kwargs):
        if cls.__module__ != __name__:
            bcs = _BaseCondition
            bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

            msg = f"type '{bcs_repr}' is not an acceptable base type"
            raise TypeError(msg)

        super().__init_subclass__(**kwargs)

    def __reduce__(self, /):
        return (Condition, (self.lock,))

    def __repr__(self, /):
        cls = Condition
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        return f"{cls_repr}({self.lock!r})"

    def __bool__(self, /):
        return False

    async def __aenter__(self, /):
        return None

    def __enter__(self, /):
        return None

    async def __aexit__(self, /, exc_type, exc_value, traceback):
        return None

    def __exit__(self, /, exc_type, exc_value, traceback):
        return None

    def __await__(self, /):
        self._waiters.append(
            token := (
                event := AsyncEvent(),
                self.timer(),
            )
        )

        success = False

        try:
            success = yield from event.__await__()
        finally:
            if not success:
                if event.cancelled():
                    try:
                        self._waiters.remove(token)
                    except ValueError:
                        pass
                else:
                    self.notify()

        return success

    def wait(self, /, timeout=None):
        self._waiters.append(
            token := (
                event := GreenEvent(),
                self.timer(),
            )
        )

        success = False

        try:
            success = event.wait(timeout)
        finally:
            if not success:
                if event.cancelled():
                    try:
                        self._waiters.remove(token)
                    except ValueError:
                        pass
                else:
                    self.notify()

        return success

    def notify(self, /, count=1, *, deadline=None):
        waiters = self._waiters

        notified = 0

        while waiters and notified != count:
            try:
                token = waiters[0]
            except IndexError:
                break
            else:
                event, time = token

                if deadline is None:
                    deadline = self.timer()

                if time > deadline:
                    break

                if event.set():
                    notified += 1

                try:
                    waiters.remove(token)
                except ValueError:
                    pass

        return notified

    def notify_all(self, /, *, deadline=None):
        waiters = self._waiters

        notified = 0

        while waiters:
            try:
                token = waiters[0]
            except IndexError:
                break
            else:
                event, time = token

                if deadline is None:
                    deadline = self.timer()

                if time > deadline:
                    break

                if event.set():
                    notified += 1

                try:
                    waiters.remove(token)
                except ValueError:
                    pass

        return notified

    @property
    def waiting(self, /):
        return len(self._waiters)


class _MixedCondition(_BaseCondition):
    __slots__ = ("__counts",)

    def __new__(cls, /, lock, timer):
        self = super().__new__(cls, lock, timer)

        self.__counts = defaultdict(int)

        return self

    def __init_subclass__(cls, /, **kwargs):
        if cls.__module__ != __name__:
            bcs = _MixedCondition
            bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

            msg = f"type '{bcs_repr}' is not an acceptable base type"
            raise TypeError(msg)

        super().__init_subclass__(**kwargs)

    def __bool__(self, /):
        return self.lock.locked()

    async def __aenter__(self, /):
        result = await self._async_enter()

        self.__counts[current_async_task_ident()] += 1

        return result

    def __enter__(self, /):
        result = self._green_enter()

        self.__counts[current_green_task_ident()] += 1

        return result

    async def __aexit__(self, /, exc_type, exc_value, traceback):
        task = current_async_task_ident()

        count = self.__counts.pop(task, 0)

        if count < 1:
            return None

        if count > 1:
            self.__counts[task] = count - 1

        return await self._async_exit(exc_type, exc_value, traceback)

    def __exit__(self, /, exc_type, exc_value, traceback):
        task = current_green_task_ident()

        count = self.__counts.pop(task, 0)

        if count < 1:
            return None

        if count > 1:
            self.__counts[task] = count - 1

        return self._green_exit(exc_type, exc_value, traceback)

    def __await__(self, /):
        if not self._async_owned():
            msg = "cannot wait on un-acquired lock"
            raise RuntimeError(msg)

        self._waiters.append(
            token := (
                event := AsyncEvent(),
                self.timer(),
            )
        )

        success = False

        try:
            state = self._async_release_save()

            if self.__counts:
                task = current_async_task_ident()

                count = self.__counts.pop(task, 0)
            else:
                count = 0

            try:
                success = yield from event.__await__()
            finally:
                yield from self._async_acquire_restore(state).__await__()

                if count:
                    self.__counts[task] = count
        finally:
            if not success:
                if event.cancelled():
                    try:
                        self._waiters.remove(token)
                    except ValueError:
                        pass
                else:
                    self.notify()

        return success

    def wait(self, /, timeout=None):
        if not self._green_owned():
            msg = "cannot wait on un-acquired lock"
            raise RuntimeError(msg)

        self._waiters.append(
            token := (
                event := GreenEvent(),
                self.timer(),
            )
        )

        success = False

        try:
            state = self._green_release_save()

            if self.__counts:
                task = current_green_task_ident()

                count = self.__counts.pop(task, 0)
            else:
                count = 0

            try:
                success = event.wait(timeout)
            finally:
                self._green_acquire_restore(state)

                if count:
                    self.__counts[task] = count
        finally:
            if not success:
                if event.cancelled():
                    try:
                        self._waiters.remove(token)
                    except ValueError:
                        pass
                else:
                    self.notify()

        return success

    # Internal methods used for overriding

    async def _async_enter(self, /):
        return await self.lock.__aenter__()

    def _green_enter(self, /):
        return self.lock.__enter__()

    async def _async_exit(self, /, exc_type, exc_value, traceback):
        return await self.lock.__aexit__(exc_type, exc_value, traceback)

    def _green_exit(self, /, exc_type, exc_value, traceback):
        return self.lock.__exit__(exc_type, exc_value, traceback)

    def _async_owned(self, /):
        return self.lock.locked()

    def _green_owned(self, /):
        return self.lock.locked()

    @shield
    async def _async_acquire_restore(self, /, state):
        await self.lock.async_acquire()

    @shield
    def _green_acquire_restore(self, /, state):
        self.lock.green_acquire()

    def _async_release_save(self, /):
        return self.lock.async_release()

    def _green_release_save(self, /):
        return self.lock.green_release()


class _RMixedCondition(_MixedCondition):
    __slots__ = ()

    def __init_subclass__(cls, /, **kwargs):
        bcs = _RMixedCondition
        bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

        msg = f"type '{bcs_repr}' is not an acceptable base type"
        raise TypeError(msg)

    # Internal methods used for overriding

    async def _async_enter(self, /):
        return await self.lock.__aenter__()

    def _green_enter(self, /):
        return self.lock.__enter__()

    async def _async_exit(self, /, exc_type, exc_value, traceback):
        return await self.lock.__aexit__(exc_type, exc_value, traceback)

    def _green_exit(self, /, exc_type, exc_value, traceback):
        return self.lock.__exit__(exc_type, exc_value, traceback)

    def _async_owned(self, /):
        return self.lock.async_owned()

    def _green_owned(self, /):
        return self.lock.green_owned()

    @shield
    async def _async_acquire_restore(self, /, state):
        await self.lock._async_acquire_restore(state)

    @shield
    def _green_acquire_restore(self, /, state):
        self.lock._green_acquire_restore(state)

    def _async_release_save(self, /):
        return self.lock._async_release_save()

    def _green_release_save(self, /):
        return self.lock._green_release_save()


class _SyncCondition(_MixedCondition):
    __slots__ = ()

    def __init_subclass__(cls, /, **kwargs):
        bcs = _SyncCondition
        bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

        msg = f"type '{bcs_repr}' is not an acceptable base type"
        raise TypeError(msg)

    # Internal methods used for overriding

    async def _async_enter(self, /):
        return self.lock.__enter__()

    def _green_enter(self, /):
        return self.lock.__enter__()

    async def _async_exit(self, /, exc_type, exc_value, traceback):
        return self.lock.__exit__(exc_type, exc_value, traceback)

    def _green_exit(self, /, exc_type, exc_value, traceback):
        return self.lock.__exit__(exc_type, exc_value, traceback)

    def _async_owned(self, /):
        return self.lock.locked()

    def _green_owned(self, /):
        return self.lock.locked()

    async def _async_acquire_restore(self, /, state):
        self.lock.acquire()

    def _green_acquire_restore(self, /, state):
        self.lock.acquire()

    def _async_release_save(self, /):
        return self.lock.release()

    def _green_release_save(self, /):
        return self.lock.release()


class _RSyncCondition(_MixedCondition):
    __slots__ = ()

    def __init_subclass__(cls, /, **kwargs):
        bcs = _RSyncCondition
        bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

        msg = f"type '{bcs_repr}' is not an acceptable base type"
        raise TypeError(msg)

    # Internal methods used for overriding

    async def _async_enter(self, /):
        return self.lock.__enter__()

    def _green_enter(self, /):
        return self.lock.__enter__()

    async def _async_exit(self, /, exc_type, exc_value, traceback):
        return self.lock.__exit__(exc_type, exc_value, traceback)

    def _green_exit(self, /, exc_type, exc_value, traceback):
        return self.lock.__exit__(exc_type, exc_value, traceback)

    def _async_owned(self, /):
        return self.lock._is_owned()

    def _green_owned(self, /):
        return self.lock._is_owned()

    async def _async_acquire_restore(self, /, state):
        self.lock._acquire_restore(state)

    def _green_acquire_restore(self, /, state):
        self.lock._acquire_restore(state)

    def _async_release_save(self, /):
        return self.lock._release_save()

    def _green_release_save(self, /):
        return self.lock._release_save()
