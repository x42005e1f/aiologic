#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .lowlevel import (
    Event,
    async_checkpoint,
    create_async_event,
    create_green_event,
    current_async_task_ident,
    current_green_task_ident,
    green_checkpoint,
    lazydeque,
)
from .thread import current_thread_ident

if TYPE_CHECKING:
    import sys

    from types import TracebackType

    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self


class Lock:
    __slots__ = (
        "__weakref__",
        "_owner",
        "_owner_thread",
        "_releasing",
        "_unlocked",
        "_waiters",
    )

    def __new__(cls, /) -> Self:
        self = object.__new__(cls)

        self._owner = None
        self._owner_thread = None

        self._releasing = False
        self._unlocked = [None]
        self._waiters = lazydeque()

        return self

    def __getnewargs__(self, /) -> tuple[Any, ...]:
        return ()

    def __getstate__(self, /) -> None:
        return None

    def __copy__(self, /) -> Self:
        return self.__class__()

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
        thread: int,
        task: tuple[str, int],
        count: int = 1,
        *,
        blocking: bool = True,
        timeout: float | None = None,
        _shield: bool = False,
    ) -> bool:
        if self._owner == task and not self._releasing:
            msg = "the current task is already holding this lock"
            raise RuntimeError(msg)

        if self._acquire_nowait():
            self._owner = task
            self._owner_thread = thread

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
                event := create_async_event(shield=_shield),
                thread,
                task,
                count,
            )
        )

        if self._acquire_nowait():
            event.set()

            self._waiters.remove(token)

            self._owner = task
            self._owner_thread = thread

        success = False

        try:
            success = await event.with_(timeout)
        finally:
            if success:
                self._releasing = False
            else:
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
        thread: int,
        task: tuple[str, int],
        count: int = 1,
        *,
        blocking: bool = True,
        timeout: float | None = None,
        _shield: bool = False,
    ) -> bool:
        if self._owner == task and not self._releasing:
            msg = "the current task is already holding this lock"
            raise RuntimeError(msg)

        if self._owner_thread == thread and not self._releasing:
            if self._owner[0] != "threading" and task[0] == "threading":
                msg = "the current thread is already holding this lock"
                raise RuntimeError(msg)

        if self._acquire_nowait():
            self._owner = task
            self._owner_thread = thread

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
                event := create_green_event(shield=_shield),
                thread,
                task,
                count,
            )
        )

        if self._acquire_nowait():
            event.set()

            self._waiters.remove(token)

            self._owner = task
            self._owner_thread = thread

        success = False

        try:
            success = event.wait(timeout)
        finally:
            if success:
                self._releasing = False
            else:
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
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> bool:
        return await self._async_acquire_on_behalf_of(
            current_thread_ident(),
            current_async_task_ident(),
            blocking=blocking,
            timeout=timeout,
        )

    def green_acquire(
        self,
        /,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> bool:
        return self._green_acquire_on_behalf_of(
            current_thread_ident(),
            current_green_task_ident(),
            blocking=blocking,
            timeout=timeout,
        )

    def _release(self, /) -> None:
        waiters = self._waiters

        while True:
            self._releasing = True

            while waiters:
                try:
                    (
                        event,
                        self._owner_thread,
                        self._owner,
                        _,
                    ) = waiters.popleft()
                except IndexError:
                    break
                else:
                    if event.set():
                        return

            self._owner = None
            self._owner_thread = None

            self._releasing = False
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

        if self._owner != task or self._releasing:
            msg = "the current task is not holding this lock"
            raise RuntimeError(msg)

        self._release()

    def green_release(self, /) -> None:
        if self._owner is None:
            msg = "release unlocked lock"
            raise RuntimeError(msg)

        task = current_green_task_ident()

        if self._owner != task or self._releasing:
            msg = "the current task is not holding this lock"
            raise RuntimeError(msg)

        self._release()

    def async_owned(self, /) -> bool:
        return (
            self._owner == current_async_task_ident() and not self._releasing
        )

    def green_owned(self, /) -> bool:
        return (
            self._owner == current_green_task_ident() and not self._releasing
        )

    def locked(self, /) -> bool:
        return not self._unlocked

    @property
    def owner(self, /) -> tuple[str, int] | None:
        return self._owner

    @property
    def waiting(self, /) -> int:
        return len(self._waiters)

    def _park(self, /, token: list[Any]) -> bool:
        event = token[0]
        state = token[6]

        if event.cancelled():
            return False

        self._waiters.append(lock_token := (event, *state))

        token[5] = True

        if event.cancelled():
            try:
                self._waiters.remove(lock_token)
            except ValueError:
                pass

            return False

        return True

    def _unpark(
        self,
        /,
        event: Event,
        state: tuple[tuple[str, int], int] | None = None,
    ) -> None:
        if state is not None:
            try:
                self._waiters.remove((event, *state))
            except ValueError:
                pass

    def _after_park(self, /) -> None:
        self._releasing = False


class RLock(Lock):
    __slots__ = ("_count",)

    def __new__(cls, /) -> Self:
        self = object.__new__(cls)

        self._count = 0
        self._owner = None
        self._owner_thread = None

        self._releasing = False
        self._unlocked = [None]
        self._waiters = lazydeque()

        return self

    async def _async_acquire_on_behalf_of(
        self,
        /,
        thread: int,
        task: tuple[str, int],
        count: int = 1,
        *,
        blocking: bool = True,
        timeout: float | None = None,
        _shield: bool = False,
    ) -> bool:
        if count < 1:
            msg = "count must be >= 1"
            raise ValueError(msg)

        if self._owner == task and not self._releasing:
            if blocking:
                await async_checkpoint()

            self._count += count

            return True

        if self._acquire_nowait():
            self._count = count
            self._owner = task
            self._owner_thread = thread

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
                event := create_async_event(shield=_shield),
                thread,
                task,
                count,
            )
        )

        if self._acquire_nowait():
            event.set()

            self._waiters.remove(token)

            self._count = count
            self._owner = task
            self._owner_thread = thread

        success = False

        try:
            success = await event.with_(timeout)
        finally:
            if success:
                self._releasing = False
            else:
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
        thread: int,
        task: tuple[str, int],
        count: int = 1,
        *,
        blocking: bool = True,
        timeout: float | None = None,
        _shield: bool = False,
    ) -> bool:
        if count < 1:
            msg = "count must be >= 1"
            raise ValueError(msg)

        if self._owner == task and not self._releasing:
            if blocking:
                green_checkpoint()

            self._count += count

            return True

        if self._owner_thread == thread and not self._releasing:
            if self._owner[0] != "threading" and task[0] == "threading":
                msg = "the current thread is already holding this lock"
                raise RuntimeError(msg)

        if self._acquire_nowait():
            self._count = count
            self._owner = task
            self._owner_thread = thread

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
                event := create_green_event(shield=_shield),
                thread,
                task,
                count,
            )
        )

        if self._acquire_nowait():
            event.set()

            self._waiters.remove(token)

            self._count = count
            self._owner = task
            self._owner_thread = thread

        success = False

        try:
            success = event.wait(timeout)
        finally:
            if success:
                self._releasing = False
            else:
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
        timeout: float | None = None,
    ) -> bool:
        return await self._async_acquire_on_behalf_of(
            current_thread_ident(),
            current_async_task_ident(),
            count,
            blocking=blocking,
            timeout=timeout,
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
            current_thread_ident(),
            current_green_task_ident(),
            count,
            blocking=blocking,
            timeout=timeout,
        )

    def _release(self, /) -> None:
        waiters = self._waiters

        while True:
            self._releasing = True

            self._count = 0

            while waiters:
                try:
                    (
                        event,
                        self._owner_thread,
                        self._owner,
                        count,
                    ) = waiters.popleft()
                except IndexError:
                    break
                else:
                    self._count = count

                    if event.set():
                        return

                    self._count = 0

            self._owner = None
            self._owner_thread = None

            self._releasing = False
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

        if self._owner != task or self._releasing:
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

        if self._owner != task or self._releasing:
            msg = "the current task is not holding this lock"
            raise RuntimeError(msg)

        if self._count < count:
            msg = "lock released too many times"
            raise RuntimeError(msg)

        self._count -= count

        if not self._count:
            self._release()

    def async_count(self, /) -> int:
        if self._owner == current_async_task_ident() and not self._releasing:
            return self._count
        else:
            return 0

    def green_count(self, /) -> int:
        if self._owner == current_green_task_ident() and not self._releasing:
            return self._count
        else:
            return 0

    @property
    def count(self, /) -> int:
        count = self._count

        if self._owner is None:
            return 0

        return count
