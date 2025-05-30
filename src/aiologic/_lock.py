#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from collections import deque
from typing import TYPE_CHECKING

from ._semaphore import BinarySemaphore
from .lowlevel import (
    async_checkpoint,
    create_async_event,
    create_green_event,
    current_async_task_ident,
    current_green_task_ident,
    green_checkpoint,
)

if sys.version_info >= (3, 13):
    from warnings import deprecated
else:
    from typing_extensions import deprecated

if TYPE_CHECKING:
    from types import TracebackType

    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self


class PLock:
    __slots__ = (
        "__weakref__",
        "_impl",
    )

    @deprecated("Use BinarySemaphore instead")
    def __new__(cls, /) -> Self:
        self = object.__new__(cls)

        self._impl = BinarySemaphore()

        return self

    def __getstate__(self, /) -> None:
        return None

    def __repr__(self, /) -> str:
        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        object_repr = f"{cls_repr}()"

        if self._impl.value > 0:
            extra = "unlocked"
        else:
            extra = f"locked, waiting={self._impl.waiting}"

        return f"<{object_repr} at {id(self):#x} [{extra}]>"

    def __bool__(self, /) -> bool:
        return not self._impl.value

    async def __aenter__(self, /) -> Self:
        await self.async_acquire()

        return self

    def __enter__(self, /) -> Self:
        self.green_acquire()

        return self

    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.async_release()

    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.green_release()

    async def async_acquire(self, /, *, blocking: bool = True) -> bool:
        return await self._impl.async_acquire(blocking=blocking)

    def green_acquire(
        self,
        /,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> bool:
        return self._impl.green_acquire(blocking=blocking, timeout=timeout)

    def _release(self, /) -> None:
        return self._impl.release()

    _async_acquire = async_acquire
    _green_acquire = green_acquire

    async_release = _release
    green_release = _release

    def locked(self, /) -> bool:
        return not self._impl.value

    @property
    def waiting(self, /) -> int:
        return self._impl.waiting


class BLock(PLock):
    __slots__ = ()

    @deprecated("Use BoundedBinarySemaphore instead")
    def __new__(cls, /) -> Self:
        self = object.__new__(cls)

        self._impl = BinarySemaphore(max_value=1)

        return self


class Lock(PLock):
    __slots__ = (
        # "__weakref__",
        "_owner",
        "_unlocked",
        "_waiters",
    )

    def __new__(cls, /) -> Self:
        self = object.__new__(cls)

        self._owner = None

        self._unlocked = [None]
        self._waiters = deque()

        return self

    def __getstate__(self, /) -> None:
        return None

    def __repr__(self, /) -> str:
        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        object_repr = f"{cls_repr}()"

        if self._unlocked:
            extra = "unlocked"
        else:
            extra = f"locked, waiting={len(self._waiters)}"

        return f"<{object_repr} at {id(self):#x} [{extra}]>"

    def __bool__(self, /) -> bool:
        return not self._unlocked

    async def __aenter__(self, /) -> Self:
        await self.async_acquire()

        return self

    def __enter__(self, /) -> Self:
        self.green_acquire()

        return self

    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.async_release()

    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.green_release()

    def _acquire_nowait(self, /) -> bool:
        if self._unlocked:
            try:
                self._unlocked.pop()
            except IndexError:
                return False
            else:
                return True

        return False

    async def _async_acquire_on_behalf_of(
        self,
        /,
        task: tuple[str, int],
        *,
        blocking: bool = True,
    ) -> bool:
        if self._owner == task:
            msg = "the current task is already holding this lock"
            raise RuntimeError(msg)

        if self._acquire_nowait():
            self._owner = task

            if blocking:
                try:
                    await async_checkpoint()
                except BaseException:
                    self._release()
                    raise

            return True

        if not blocking:
            return False

        self._waiters.append(
            token := (
                event := create_async_event(),
                task,
                1,
            )
        )

        if self._acquire_nowait():
            self._owner = task

            self._waiters.remove(token)

            event.set()

        success = False

        try:
            success = await event
        finally:
            if not success:
                if event.cancelled():
                    try:
                        self._waiters.remove(token)
                    except ValueError:
                        pass
                else:
                    self._release()

        return success

    def _green_acquire_on_behalf_of(
        self,
        /,
        task: tuple[str, int],
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> bool:
        if self._owner == task:
            msg = "the current task is already holding this lock"
            raise RuntimeError(msg)

        if self._acquire_nowait():
            self._owner = task

            if blocking:
                try:
                    green_checkpoint()
                except BaseException:
                    self._release()
                    raise

            return True

        if not blocking:
            return False

        self._waiters.append(
            token := (
                event := create_green_event(),
                task,
                1,
            )
        )

        if self._acquire_nowait():
            self._owner = task

            self._waiters.remove(token)

            event.set()

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
                    self._release()

        return success

    async def async_acquire(self, /, *, blocking: bool = True) -> bool:
        return await self._async_acquire_on_behalf_of(
            current_async_task_ident(),
            blocking=blocking,
        )

    def green_acquire(
        self,
        /,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> bool:
        return self._green_acquire_on_behalf_of(
            current_green_task_ident(),
            blocking=blocking,
            timeout=timeout,
        )

    def _release(self, /) -> None:
        waiters = self._waiters

        while True:
            while waiters:
                try:
                    event, self._owner, _ = waiters.popleft()
                except IndexError:
                    break
                else:
                    if event.set():
                        return

            self._owner = None

            self._unlocked.append(None)

            if waiters:
                try:
                    self._unlocked.pop()
                except IndexError:
                    break
            else:
                break

    def async_release(self, /) -> None:
        if self._owner is None:
            msg = "release unlocked lock"
            raise RuntimeError(msg)

        task = current_async_task_ident()

        if self._owner != task:
            msg = "the current task is not holding this lock"
            raise RuntimeError(msg)

        self._release()

    def green_release(self, /) -> None:
        if self._owner is None:
            msg = "release unlocked lock"
            raise RuntimeError(msg)

        task = current_green_task_ident()

        if self._owner != task:
            msg = "the current task is not holding this lock"
            raise RuntimeError(msg)

        self._release()

    def async_owned(self, /) -> bool:
        return self._owner == current_async_task_ident()

    def green_owned(self, /) -> bool:
        return self._owner == current_green_task_ident()

    def locked(self, /) -> bool:
        return not self._unlocked

    @property
    def owner(self, /) -> tuple[str, int] | None:
        return self._owner

    @property
    def waiting(self, /) -> int:
        return len(self._waiters)

    # Internal methods used by condition variables

    async def _async_acquire_restore(
        self,
        /,
        state: tuple[tuple[str, int], int],
    ) -> bool:
        return await self._async_acquire_on_behalf_of(state[0])

    def _green_acquire_restore(
        self,
        /,
        state: tuple[tuple[str, int], int],
    ) -> bool:
        return self._green_acquire_on_behalf_of(state[0])

    def _async_release_save(self, /) -> tuple[tuple[str, int], int]:
        state = (self._owner, 1)

        self.async_release()

        return state

    def _green_release_save(self, /) -> tuple[tuple[str, int], int]:
        state = (self._owner, 1)

        self.green_release()

        return state


class RLock(Lock):
    __slots__ = ("_count",)

    def __new__(cls, /) -> Self:
        self = object.__new__(cls)

        self._count = 0
        self._owner = None

        self._unlocked = [None]
        self._waiters = deque()

        return self

    async def _async_acquire_on_behalf_of(
        self,
        /,
        task: tuple[str, int],
        count: int = 1,
        *,
        blocking: bool = True,
    ) -> bool:
        if count < 1:
            msg = "count must be >= 1"
            raise ValueError(msg)

        if self._owner == task:
            if blocking:
                await async_checkpoint()

            self._count += count

            return True

        if self._acquire_nowait():
            self._owner = task
            self._count = count

            if blocking:
                try:
                    await async_checkpoint()
                except BaseException:
                    self._release()
                    raise

            return True

        if not blocking:
            return False

        self._waiters.append(
            token := (
                event := create_async_event(),
                task,
                count,
            )
        )

        if self._acquire_nowait():
            self._owner = task
            self._count = count

            self._waiters.remove(token)

            event.set()

        success = False

        try:
            success = await event
        finally:
            if not success:
                if event.cancelled():
                    try:
                        self._waiters.remove(token)
                    except ValueError:
                        pass
                else:
                    self._release()

        return success

    def _green_acquire_on_behalf_of(
        self,
        /,
        task: tuple[str, int],
        count: int = 1,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> bool:
        if count < 1:
            msg = "count must be >= 1"
            raise ValueError(msg)

        if self._owner == task:
            if blocking:
                green_checkpoint()

            self._count += count

            return True

        if self._acquire_nowait():
            self._owner = task
            self._count = count

            if blocking:
                try:
                    green_checkpoint()
                except BaseException:
                    self._release()
                    raise

            return True

        if not blocking:
            return False

        self._waiters.append(
            token := (
                event := create_green_event(),
                task,
                count,
            )
        )

        if self._acquire_nowait():
            self._owner = task
            self._count = count

            self._waiters.remove(token)

            event.set()

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
                    self._release()

        return success

    async def async_acquire(
        self,
        /,
        count: int = 1,
        *,
        blocking: bool = True,
    ) -> bool:
        return await self._async_acquire_on_behalf_of(
            current_async_task_ident(),
            count,
            blocking=blocking,
        )

    def green_acquire(
        self,
        /,
        count: int = 1,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> bool:
        return self._green_acquire_on_behalf_of(
            current_green_task_ident(),
            count,
            blocking=blocking,
            timeout=timeout,
        )

    def _release(self, /) -> None:
        waiters = self._waiters

        while True:
            while waiters:
                try:
                    event, self._owner, self._count = waiters.popleft()
                except IndexError:
                    break
                else:
                    if event.set():
                        return

            self._count = 0
            self._owner = None

            self._unlocked.append(None)

            if waiters:
                try:
                    self._unlocked.pop()
                except IndexError:
                    break
            else:
                break

    def async_release(self, /, count: int = 1) -> None:
        if count < 1:
            msg = "count must be >= 1"
            raise ValueError(msg)

        if self._owner is None:
            msg = "release unlocked lock"
            raise RuntimeError(msg)

        task = current_async_task_ident()

        if self._owner != task:
            msg = "the current task is not holding this lock"
            raise RuntimeError(msg)

        if self._count < count:
            msg = "lock released too many times"
            raise RuntimeError(msg)

        self._count -= count

        if not self._count:
            self._release()

    def green_release(self, /, count: int = 1) -> None:
        if count < 1:
            msg = "count must be >= 1"
            raise ValueError(msg)

        if self._owner is None:
            msg = "release unlocked lock"
            raise RuntimeError(msg)

        task = current_green_task_ident()

        if self._owner != task:
            msg = "the current task is not holding this lock"
            raise RuntimeError(msg)

        if self._count < count:
            msg = "lock released too many times"
            raise RuntimeError(msg)

        self._count -= count

        if not self._count:
            self._release()

    @property
    def count(self, /) -> int:
        return self._count

    @property
    @deprecated("Use 'count' instead")
    def level(self, /) -> int:
        return self._count

    # Internal methods used by condition variables

    async def _async_acquire_restore(
        self,
        /,
        state: tuple[tuple[str, int], int],
    ) -> bool:
        return await self._async_acquire_on_behalf_of(*state)

    def _green_acquire_restore(
        self,
        /,
        state: tuple[tuple[str, int], int],
    ) -> bool:
        return self._green_acquire_on_behalf_of(*state)

    def _async_release_save(self, /) -> tuple[tuple[str, int], int]:
        state = (self._owner, self._count)

        self.async_release()

        return state

    def _green_release_save(self, /) -> tuple[tuple[str, int], int]:
        state = (self._owner, self._count)

        self.green_release()

        return state
