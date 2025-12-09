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
from .meta import copies

if TYPE_CHECKING:
    import sys

    from types import TracebackType

    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self


class Lock:
    """..."""

    __slots__ = (
        "__weakref__",
        "_owner",
        "_releasing",
        "_unlocked",
        "_waiters",
    )

    def __new__(cls, /) -> Self:
        """..."""

        self = object.__new__(cls)

        self._owner = None

        self._releasing = False
        self._unlocked = [None]
        self._waiters = lazydeque()

        return self

    def __getnewargs__(self, /) -> tuple[Any, ...]:
        """
        Returns arguments that can be used to create new instances with the
        same initial values.

        Used by:

        * The :mod:`pickle` module for pickling.
        * The :mod:`copy` module for copying.

        The current state does not affect the arguments.

        Example:
            >>> orig = Lock()
            >>> copy = Lock(*orig.__getnewargs__())
        """

        return ()

    def __getstate__(self, /) -> None:
        """
        Disables the use of internal state for pickling and copying.
        """

        return None

    def __copy__(self, /) -> Self:
        """..."""

        return self.__class__()

    def __repr__(self, /) -> str:
        """..."""

        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        object_repr = f"{cls_repr}()"

        if self._unlocked:
            extra = "unlocked"
        else:
            extra = f"locked, waiting={len(self._waiters)}"

        return f"<{object_repr} at {id(self):#x} [{extra}]>"

    def __bool__(self, /) -> bool:
        """
        Returns :data:`True` if the lock is used by any task.

        Used by the standard :ref:`truth testing procedure <truth>`.

        Example:
            >>> writing = Lock()
            >>> bool(writing)
            False
            >>> with writing:  # lock is in use
            ...     bool(writing)
            True
            >>> bool(writing)
            False
        """

        return not self._unlocked

    async def __aenter__(self, /) -> Self:
        """..."""

        await self.async_acquire()

        return self

    def __enter__(self, /) -> Self:
        """..."""

        self.green_acquire()

        return self

    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """..."""

        self.async_release()

    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """..."""

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
        count: int = 1,
        *,
        blocking: bool = True,
        _shield: bool = False,
    ) -> bool:
        if self._owner == task and not self._releasing:
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
                event := create_async_event(shield=_shield),
                task,
                count,
            )
        )

        if self._acquire_nowait():
            event.set()

            self._waiters.remove(token)

            self._owner = task

        success = False

        try:
            success = await event
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
                task,
                count,
            )
        )

        if self._acquire_nowait():
            event.set()

            self._waiters.remove(token)

            self._owner = task

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

    async def async_acquire(self, /, *, blocking: bool = True) -> bool:
        """..."""

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
        """..."""

        return self._green_acquire_on_behalf_of(
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
                    event, self._owner, _ = waiters.popleft()
                except IndexError:
                    break
                else:
                    if event.set():
                        return

            self._owner = None

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
        """..."""

        if self._owner is None:
            msg = "release unlocked lock"
            raise RuntimeError(msg)

        task = current_async_task_ident()

        if self._owner != task or self._releasing:
            msg = "the current task is not holding this lock"
            raise RuntimeError(msg)

        self._release()

    def green_release(self, /) -> None:
        """..."""

        if self._owner is None:
            msg = "release unlocked lock"
            raise RuntimeError(msg)

        task = current_green_task_ident()

        if self._owner != task or self._releasing:
            msg = "the current task is not holding this lock"
            raise RuntimeError(msg)

        self._release()

    def async_owned(self, /) -> bool:
        """
        Return :data:`True` if the current async task owns the lock.

        Unlike the :attr:`owner` property, always reliable.

        Example:
            >>> lock = Lock()
            >>> lock.async_owned()
            False
            >>> async with lock:
            ...     lock.async_owned()
            True
            >>> lock.async_owned()
            False
        """

        return (
            self._owner == current_async_task_ident() and not self._releasing
        )

    def green_owned(self, /) -> bool:
        """
        Return :data:`True` if the current green task owns the lock.

        Unlike the :attr:`owner` property, always reliable.

        Example:
            >>> lock = Lock()
            >>> lock.green_owned()
            False
            >>> with lock:
            ...     lock.green_owned()
            True
            >>> lock.green_owned()
            False
        """

        return (
            self._owner == current_green_task_ident() and not self._releasing
        )

    def locked(self, /) -> bool:
        """
        Return :data:`True` if anyone owns the lock.

        Example:
            >>> import asyncio
            >>> async def own_the_lock():
            ...     async with lock:
            ...         await asyncio.sleep(3600)
            >>> lock = Lock()
            >>> lock.locked()
            False
            >>> task = asyncio.create_task(own_the_lock())
            >>> lock.locked()
            True
            >>> task.cancel()
            >>> lock.locked()
            False
        """

        return not self._unlocked

    @property
    def owner(self, /) -> tuple[str, int] | None:
        """
        The current identifier of the task that owns the lock, or :data:`None`
        if no one owns the lock.

        It is not reliable during release, as it may temporarily be the
        identifier of a task that has cancelled the :meth:`async_acquire` or
        :meth:`green_acquire` call (e.g., due to a timeout).
        """

        return self._owner

    @property
    def waiting(self, /) -> int:
        """
        The current number of tasks waiting to own.

        It represents the length of the waiting queue and thus changes
        immediately.
        """

        return len(self._waiters)

    # Internal methods used by condition variables

    def _park(self, /, token: list[Any]) -> bool:
        event = token[0]
        state = token[6]

        if event.cancelled():
            return False

        self._waiters.append(lock_token := (event, *state))

        token[5] = True  # reparked

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
    """..."""

    __slots__ = ("_count",)

    def __new__(cls, /) -> Self:
        """..."""

        self = object.__new__(cls)

        self._count = 0
        self._owner = None

        self._releasing = False
        self._unlocked = [None]
        self._waiters = lazydeque()

        return self

    @copies(Lock.__getnewargs__)
    def __getnewargs__(self, /) -> tuple[Any, ...]:
        """
        Returns arguments that can be used to create new instances with the
        same initial values.

        Used by:

        * The :mod:`pickle` module for pickling.
        * The :mod:`copy` module for copying.

        The current state does not affect the arguments.

        Example:
            >>> orig = RLock()
            >>> copy = RLock(*orig.__getnewargs__())
        """

        return Lock.__getnewargs__(self)

    @copies(Lock.__getstate__)
    def __getstate__(self, /) -> None:
        """
        Disables the use of internal state for pickling and copying.
        """

        return Lock.__getstate__(self)

    @copies(Lock.__copy__)
    def __copy__(self, /) -> Self:
        """..."""

        return Lock.__copy__(self)

    @copies(Lock.__repr__)
    def __repr__(self, /) -> str:
        """..."""

        return Lock.__repr__(self)

    @copies(Lock.__bool__)
    def __bool__(self, /) -> bool:
        """
        Returns :data:`True` if the lock is used by any task.

        Used by the standard :ref:`truth testing procedure <truth>`.

        Example:
            >>> writing = RLock()
            >>> bool(writing)
            False
            >>> with writing:  # lock is in use
            ...     bool(writing)
            True
            >>> bool(writing)
            False
        """

        return Lock.__bool__(self)

    @copies(Lock.__aenter__)
    async def __aenter__(self, /) -> Self:
        """..."""

        return await Lock.__aenter__(self)

    @copies(Lock.__enter__)
    def __enter__(self, /) -> Self:
        """..."""

        return Lock.__enter__(self)

    @copies(Lock.__aexit__)
    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """..."""

        return await Lock.__aexit__(self, exc_type, exc_value, traceback)

    @copies(Lock.__exit__)
    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """..."""

        return Lock.__exit__(self, exc_type, exc_value, traceback)

    async def _async_acquire_on_behalf_of(
        self,
        /,
        task: tuple[str, int],
        count: int = 1,
        *,
        blocking: bool = True,
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
                task,
                count,
            )
        )

        if self._acquire_nowait():
            event.set()

            self._waiters.remove(token)

            self._count = count
            self._owner = task

        success = False

        try:
            success = await event
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

        if self._acquire_nowait():
            self._count = count
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
                event := create_green_event(shield=_shield),
                task,
                count,
            )
        )

        if self._acquire_nowait():
            event.set()

            self._waiters.remove(token)

            self._count = count
            self._owner = task

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
    ) -> bool:
        """..."""

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
        """..."""

        return self._green_acquire_on_behalf_of(
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
                    event, self._owner, count = waiters.popleft()
                except IndexError:
                    break
                else:
                    self._count = count

                    if event.set():
                        return

                    self._count = 0

            self._owner = None

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
        """..."""

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
        """..."""

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

    @copies(Lock.async_owned)
    def async_owned(self, /) -> bool:
        """
        Return :data:`True` if the current async task owns the lock.

        Unlike the :attr:`owner` property, always reliable.

        Example:
            >>> lock = RLock()
            >>> lock.async_owned()
            False
            >>> async with lock:
            ...     lock.async_owned()
            True
            >>> lock.async_owned()
            False
        """

        return Lock.async_owned(self)

    @copies(Lock.green_owned)
    def green_owned(self, /) -> bool:
        """
        Return :data:`True` if the current green task owns the lock.

        Unlike the :attr:`owner` property, always reliable.

        Example:
            >>> lock = RLock()
            >>> lock.green_owned()
            False
            >>> with lock:
            ...     lock.green_owned()
            True
            >>> lock.green_owned()
            False
        """

        return Lock.green_owned(self)

    def async_count(self, /) -> int:
        """
        Return the recursion level of the current async task.

        Unlike the :attr:`count` property, always reliable.

        Example:
            >>> lock = RLock()
            >>> lock.async_count()
            0
            >>> async with lock:
            ...     lock.async_count()
            1
            >>> lock.async_count()
            0
        """

        if self._owner == current_async_task_ident() and not self._releasing:
            return self._count
        else:
            return 0

    def green_count(self, /) -> int:
        """
        Return the recursion level of the current green task.

        Unlike the :attr:`count` property, always reliable.

        Example:
            >>> lock = RLock()
            >>> lock.green_count()
            0
            >>> with lock:
            ...     lock.green_count()
            1
            >>> lock.green_count()
            0
        """

        if self._owner == current_green_task_ident() and not self._releasing:
            return self._count
        else:
            return 0

    @copies(Lock.locked)
    def locked(self, /) -> bool:
        """
        Return :data:`True` if anyone owns the lock.

        Example:
            >>> import asyncio
            >>> async def own_the_lock():
            ...     async with lock:
            ...         await asyncio.sleep(3600)
            >>> lock = RLock()
            >>> lock.locked()
            False
            >>> task = asyncio.create_task(own_the_lock())
            >>> lock.locked()
            True
            >>> task.cancel()
            >>> lock.locked()
            False
        """

        return Lock.locked(self)

    @property
    @copies(Lock.owner.fget)
    def owner(self, /) -> tuple[str, int] | None:
        """
        The current identifier of the task that owns the lock, or :data:`None`
        if no one owns the lock.

        It is not reliable during release, as it may temporarily be the
        identifier of a task that has cancelled the :meth:`async_acquire` or
        :meth:`green_acquire` call (e.g., due to a timeout).
        """

        return Lock.owner.fget(self)

    @property
    def count(self, /) -> int:
        """
        The current recursion level of the task that owns the lock, or
        :data:`0` if no one owns the lock.

        It is not reliable during release, as it may temporarily be the
        recursion level of a task that has cancelled the :meth:`async_acquire`
        or :meth:`green_acquire` call (e.g., due to a timeout).
        """

        count = self._count

        if self._owner is None:
            return 0

        return count

    @property
    @copies(Lock.waiting.fget)
    def waiting(self, /) -> int:
        """
        The current number of tasks waiting to own.

        It represents the length of the waiting queue and thus changes
        immediately.
        """

        return Lock.waiting.fget(self)
