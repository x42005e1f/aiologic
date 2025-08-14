#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import warnings

from collections import deque
from typing import TYPE_CHECKING, Any

from ._semaphore import BinarySemaphore
from .lowlevel import (
    Event,
    async_checkpoint,
    create_async_event,
    create_green_event,
    current_async_task_ident,
    current_green_task_ident,
    green_checkpoint,
)
from .lowlevel._utils import _copies as copies

if TYPE_CHECKING:
    import sys

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

    def __new__(cls, /) -> Self:
        warnings.warn(
            "Use BinarySemaphore instead",
            DeprecationWarning,
            stacklevel=2,
        )

        self = object.__new__(cls)

        self._impl = BinarySemaphore()

        return self

    def __init_subclass__(cls, /, **kwargs: Any) -> None:
        if cls.__module__ != __name__:
            warnings.warn(
                "Use BinarySemaphore instead",
                DeprecationWarning,
                stacklevel=2,
            )

        super().__init_subclass__(**kwargs)

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

    # Internal methods used by condition variables

    def _park(self, /, token: list[Any]) -> bool:
        return self._impl._park(token)

    def _unpark(self, /, event: Event) -> None:
        return self._impl._unpark(event)

    def _after_park(self, /) -> None:
        return self._impl._after_park()


class BLock(PLock):
    __slots__ = ()

    def __new__(cls, /) -> Self:
        warnings.warn(
            "Use BoundedBinarySemaphore instead",
            DeprecationWarning,
            stacklevel=2,
        )

        self = object.__new__(cls)

        self._impl = BinarySemaphore(max_value=1)

        return self

    def __init_subclass__(cls, /, **kwargs: Any) -> None:
        warnings.warn(
            "Use BoundedBinarySemaphore instead",
            DeprecationWarning,
            stacklevel=2,
        )

        super().__init_subclass__(**kwargs)


class Lock(PLock):
    """..."""

    __slots__ = (
        # "__weakref__",
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
        self._waiters = deque()

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
        """..."""

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
            self._owner = task

            self._waiters.remove(token)

            event.set()

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
            self._owner = task

            self._waiters.remove(token)

            event.set()

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
        """..."""

        return (
            self._owner == current_async_task_ident() and not self._releasing
        )

    def green_owned(self, /) -> bool:
        """..."""

        return (
            self._owner == current_green_task_ident() and not self._releasing
        )

    def locked(self, /) -> bool:
        """..."""

        return not self._unlocked

    @property
    def owner(self, /) -> tuple[str, int] | None:
        """..."""

        return self._owner

    @property
    def waiting(self, /) -> int:
        """..."""

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
        self._waiters = deque()

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

    @copies(Lock.__repr__)
    def __repr__(self, /) -> str:
        """..."""

        return Lock.__repr__(self)

    @copies(Lock.__bool__)
    def __bool__(self, /) -> bool:
        """..."""

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
                event := create_async_event(shield=_shield),
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
                event := create_green_event(shield=_shield),
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
        """..."""

        return Lock.async_owned(self)

    @copies(Lock.green_owned)
    def green_owned(self, /) -> bool:
        """..."""

        return Lock.green_owned(self)

    @copies(Lock.locked)
    def locked(self, /) -> bool:
        """..."""

        return Lock.locked(self)

    @property
    @copies(Lock.owner.fget)
    def owner(self, /) -> tuple[str, int] | None:
        """..."""

        return Lock.owner.fget(self)

    @property
    def count(self, /) -> int:
        """..."""

        return self._count

    @property
    def level(self, /) -> int:
        warnings.warn("Use 'count' instead", DeprecationWarning, stacklevel=2)

        return self._count

    @property
    @copies(Lock.waiting.fget)
    def waiting(self, /) -> int:
        """..."""

        return Lock.waiting.fget(self)
