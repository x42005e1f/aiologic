#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import os
import platform
import sys

from typing import TYPE_CHECKING, Any, Final

from .lowlevel import (
    Event,
    ThreadOnceLock,
    async_checkpoint,
    create_async_event,
    create_green_event,
    green_checkpoint,
    lazydeque,
)
from .meta import DEFAULT, DefaultType, copies

if sys.version_info >= (3, 11):
    from typing import overload
else:
    from typing_extensions import overload

if TYPE_CHECKING:
    from types import TracebackType

    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self

__PYTHON_IMPLEMENTATION = platform.python_implementation()

try:
    from sys import _is_gil_enabled
except ImportError:
    __GIL_ENABLED: Final[bool] = True
else:
    __GIL_ENABLED: Final[bool] = _is_gil_enabled()

_USE_DELATTR: Final[bool] = (
    __GIL_ENABLED or sys.version_info >= (3, 14)  # see python/cpython#127266
)
_USE_BYTEARRAY: Final[bool] = __PYTHON_IMPLEMENTATION == "CPython" and (
    __GIL_ENABLED or sys.version_info >= (3, 14)  # see python/cpython#129107
)

_PERFECT_FAIRNESS_ENABLED: Final[bool] = bool(
    os.getenv(
        "AIOLOGIC_PERFECT_FAIRNESS",
        "1" if __GIL_ENABLED else "",
    )
)

_USE_ONCELOCK: Final[bool] = _PERFECT_FAIRNESS_ENABLED and not __GIL_ENABLED


class Semaphore:
    """..."""

    __slots__ = (
        "__weakref__",
        "_initial_value",
        "_unlocked",
        "_waiters",
    )

    @overload
    def __new__(
        cls,
        /,
        initial_value: int | DefaultType = DEFAULT,
        max_value: None = None,
    ) -> Self: ...
    @overload
    def __new__(
        cls,
        /,
        initial_value: int | DefaultType,
        max_value: int | DefaultType,
    ) -> BoundedSemaphore: ...
    @overload
    def __new__(
        cls,
        /,
        *,
        max_value: int | DefaultType,
    ) -> BoundedSemaphore: ...
    def __new__(cls, /, initial_value=DEFAULT, max_value=None):
        """..."""

        if max_value is not None:
            if cls is not Semaphore:
                msg = (
                    "max_value must be None for subclasses."
                    " Did you want to inherit BoundedSemaphore instead?"
                )
                raise TypeError(msg)

            return BoundedSemaphore.__new__(
                BoundedSemaphore,
                initial_value,
                max_value,
            )

        self = object.__new__(cls)

        if initial_value is not DEFAULT:
            if initial_value < 0:
                msg = "initial_value must be >= 0"
                raise ValueError(msg)

            self._initial_value = initial_value
        else:
            self._initial_value = 1

        if _USE_BYTEARRAY:
            self._unlocked = bytearray(self._initial_value)
        else:
            self._unlocked = [None] * self._initial_value

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
            >>> orig = Semaphore(2)
            >>> orig.initial_value
            2
            >>> copy = Semaphore(*orig.__getnewargs__())
            >>> copy.initial_value
            2
        """

        return (self._initial_value,)

    def __getstate__(self, /) -> None:
        """
        Disables the use of internal state for pickling and copying.
        """

        return None

    def __copy__(self, /) -> Self:
        """..."""

        return self.__class__(self._initial_value)

    def __repr__(self, /) -> str:
        """..."""

        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        object_repr = f"{cls_repr}({self._initial_value!r})"

        value = len(self._unlocked)

        if value > 0:
            extra = f"value={value}"
        else:
            extra = f"value={value}, waiting={len(self._waiters)}"

        return f"<{object_repr} at {id(self):#x} [{extra}]>"

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

    async def _async_acquire(
        self,
        /,
        *,
        blocking: bool = True,
        _shield: bool = False,
    ) -> bool:
        if self._acquire_nowait():
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
            event := create_async_event(
                locking=(
                    _USE_ONCELOCK and not isinstance(self, BinarySemaphore)
                ),
                shield=_shield,
            )
        )

        if self._acquire_nowait():
            if event.set():
                try:
                    self._waiters.remove(event)
                except ValueError:
                    pass
            else:
                self._release()

        success = False

        try:
            success = await event
        finally:
            if not success:
                if event.cancelled():
                    try:
                        self._waiters.remove(event)
                    except ValueError:
                        pass
                else:
                    self._release()

        return success

    def _green_acquire(
        self,
        /,
        *,
        blocking: bool = True,
        timeout: float | None = None,
        _shield: bool = False,
    ) -> bool:
        if self._acquire_nowait():
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
            event := create_green_event(
                locking=(
                    _USE_ONCELOCK and not isinstance(self, BinarySemaphore)
                ),
                shield=_shield,
            )
        )

        if self._acquire_nowait():
            if event.set():
                try:
                    self._waiters.remove(event)
                except ValueError:
                    pass
            else:
                self._release()

        success = False

        try:
            success = event.wait(timeout)
        finally:
            if not success:
                if event.cancelled():
                    try:
                        self._waiters.remove(event)
                    except ValueError:
                        pass
                else:
                    self._release()

        return success

    async def async_acquire(self, /, *, blocking: bool = True) -> bool:
        """..."""

        return await self._async_acquire(blocking=blocking)

    def green_acquire(
        self,
        /,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> bool:
        """..."""

        return self._green_acquire(blocking=blocking, timeout=timeout)

    def _release(self, /, count: int = 1) -> None:
        waiters = self._waiters

        while True:
            while waiters and count:
                try:
                    if _PERFECT_FAIRNESS_ENABLED:
                        event = waiters[0]
                    else:
                        event = waiters.popleft()
                except IndexError:
                    break
                else:
                    if remove := event.set():
                        count -= 1

                    if _PERFECT_FAIRNESS_ENABLED:
                        try:
                            if remove or waiters[0] is event:
                                if _USE_ONCELOCK:
                                    ThreadOnceLock.acquire(event)
                                    try:
                                        if waiters[0] is event:
                                            waiters.remove(event)
                                    finally:
                                        ThreadOnceLock.release(event)
                                else:
                                    waiters.remove(event)
                        except ValueError:  # waiters does not contain event
                            continue
                        except IndexError:  # waiters is empty
                            break

            if count < 1:
                break
            elif count == 1:
                if _USE_BYTEARRAY:
                    self._unlocked.append(0)
                else:
                    self._unlocked.append(None)
            else:
                if _USE_BYTEARRAY:
                    self._unlocked.extend(b"\x00" * count)
                else:
                    self._unlocked.extend([None] * count)

            if waiters:
                try:
                    self._unlocked.pop()
                except IndexError:
                    break
                else:
                    count = 1
            else:
                break

    @copies(_release)
    def release(self, /, count: int = 1) -> None:
        """..."""

        return self._release(count)

    @copies(release)
    def async_release(self, /, count: int = 1) -> None:
        """..."""

        return self.release(count)

    @copies(release)
    def green_release(self, /, count: int = 1) -> None:
        """..."""

        return self.release(count)

    @property
    def initial_value(self, /) -> int:
        """
        The initial number of permits available for acquiring.
        """

        return self._initial_value

    @property
    def value(self, /) -> int:
        """
        The current number of permits available to be acquired.

        It may not change after release if all the released permits have been
        reassigned to waiting tasks.
        """

        return len(self._unlocked)

    @property
    def waiting(self, /) -> int:
        """
        The current number of tasks waiting to acquire.

        It represents the length of the waiting queue and thus changes
        immediately.
        """

        return len(self._waiters)


class BoundedSemaphore(Semaphore):
    """..."""

    __slots__ = (
        "_locked",
        "_max_value",
    )

    def __new__(
        cls,
        /,
        initial_value: int | DefaultType = DEFAULT,
        max_value: int | DefaultType = DEFAULT,
    ) -> Self:
        """..."""

        if (
            cls is BoundedSemaphore
            and (initial_value is DEFAULT or initial_value <= 1)
            and (max_value is DEFAULT or max_value <= 1)
        ):
            return BoundedBinarySemaphore.__new__(
                BoundedBinarySemaphore,
                initial_value,
                max_value,
            )

        self = object.__new__(cls)

        if initial_value is not DEFAULT:
            if initial_value < 0:
                msg = "initial_value must be >= 0"
                raise ValueError(msg)

            self._initial_value = initial_value
        elif max_value is not DEFAULT:
            self._initial_value = max_value
        else:
            self._initial_value = 1

        if max_value is not DEFAULT:
            if max_value < 0:
                msg = "max_value must be >= 0"
                raise ValueError(msg)

            if max_value < self._initial_value:
                msg = "max_value must be >= initial_value"
                raise ValueError(msg)

            self._max_value = max_value
        else:
            self._max_value = self._initial_value

        if _USE_BYTEARRAY:
            self._locked = bytearray(self._max_value - self._initial_value)
            self._unlocked = bytearray(self._initial_value)
        else:
            self._locked = [None] * (self._max_value - self._initial_value)
            self._unlocked = [None] * self._initial_value

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
            >>> orig = BoundedSemaphore(2)
            >>> orig.max_value
            2
            >>> copy = BoundedSemaphore(*orig.__getnewargs__())
            >>> copy.max_value
            2
        """

        return (self._initial_value, self._max_value)

    def __getstate__(self, /) -> None:
        """
        Disables the use of internal state for pickling and copying.
        """

        return None

    def __copy__(self, /) -> Self:
        """..."""

        return self.__class__(self._initial_value, self._max_value)

    def __repr__(self, /) -> str:
        """..."""

        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        initial_value = self._initial_value
        max_value = self._max_value

        if initial_value == max_value:
            args_repr = f"{initial_value!r}"
        else:
            args_repr = f"{initial_value!r}, max_value={max_value!r}"

        object_repr = f"{cls_repr}({args_repr})"

        value = len(self._unlocked)

        if value > 0:
            extra = f"value={value}"
        else:
            extra = f"value={value}, waiting={len(self._waiters)}"

        return f"<{object_repr} at {id(self):#x} [{extra}]>"

    @copies(Semaphore.__aenter__)
    async def __aenter__(self, /) -> Self:
        """..."""

        return await Semaphore.__aenter__(self)

    @copies(Semaphore.__enter__)
    def __enter__(self, /) -> Self:
        """..."""

        return Semaphore.__enter__(self)

    @copies(Semaphore.__aexit__)
    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """..."""

        return await Semaphore.__aexit__(self, exc_type, exc_value, traceback)

    @copies(Semaphore.__exit__)
    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """..."""

        return Semaphore.__exit__(self, exc_type, exc_value, traceback)

    async def async_acquire(self, /, *, blocking: bool = True) -> bool:
        """..."""

        success = await self._async_acquire(blocking=blocking)

        if success:
            if _USE_BYTEARRAY:
                self._locked.append(0)
            else:
                self._locked.append(None)

        return success

    def green_acquire(
        self,
        /,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> bool:
        """..."""

        success = self._green_acquire(blocking=blocking, timeout=timeout)

        if success:
            if _USE_BYTEARRAY:
                self._locked.append(0)
            else:
                self._locked.append(None)

        return success

    def release(self, /, count: int = 1) -> None:
        """..."""

        if count != 1:
            msg = "count must be 1"
            raise ValueError(msg)

        try:
            self._locked.pop()
        except IndexError:
            msg = "semaphore released too many times"
            raise RuntimeError(msg) from None

        self._release(count)

    @copies(release)
    def async_release(self, /, count: int = 1) -> None:
        """..."""

        return self.release(count)

    @copies(release)
    def green_release(self, /, count: int = 1) -> None:
        """..."""

        return self.release(count)

    @property
    @copies(Semaphore.initial_value.fget)
    def initial_value(self, /) -> int:
        """
        The initial number of permits available for acquiring.
        """

        return Semaphore.initial_value.fget(self)

    @property
    def max_value(self, /) -> int:
        """
        The maximum number of permits which the semaphore can hold.
        """

        return self._max_value

    @property
    @copies(Semaphore.value.fget)
    def value(self, /) -> int:
        """
        The current number of permits available to be acquired.

        It may not change after release if all the released permits have been
        reassigned to waiting tasks.
        """

        return Semaphore.value.fget(self)

    @property
    @copies(Semaphore.waiting.fget)
    def waiting(self, /) -> int:
        """
        The current number of tasks waiting to acquire.

        It represents the length of the waiting queue and thus changes
        immediately.
        """

        return Semaphore.waiting.fget(self)


class BinarySemaphore(Semaphore):
    """..."""

    __slots__ = ()

    @overload
    def __new__(
        cls,
        /,
        initial_value: int | DefaultType = DEFAULT,
        max_value: None = None,
    ) -> Self: ...
    @overload
    def __new__(
        cls,
        /,
        initial_value: int | DefaultType,
        max_value: int | DefaultType,
    ) -> BoundedBinarySemaphore: ...
    @overload
    def __new__(
        cls,
        /,
        *,
        max_value: int | DefaultType,
    ) -> BoundedBinarySemaphore: ...
    def __new__(cls, /, initial_value=DEFAULT, max_value=None):
        """..."""

        if max_value is not None:
            if cls is not BinarySemaphore:
                msg = (
                    "max_value must be None for subclasses."
                    " Did you want to inherit BoundedBinarySemaphore instead?"
                )
                raise TypeError(msg)

            return BoundedBinarySemaphore.__new__(
                BoundedBinarySemaphore,
                initial_value,
                max_value,
            )

        self = object.__new__(cls)

        if initial_value is not DEFAULT:
            if initial_value < 0 or 1 < initial_value:
                msg = "initial_value must be 0 or 1"
                raise ValueError(msg)

            self._initial_value = initial_value
        else:
            self._initial_value = 1

        self._unlocked = [None] * self._initial_value

        self._waiters = lazydeque()

        return self

    @copies(Semaphore.__getnewargs__)
    def __getnewargs__(self, /) -> tuple[Any, ...]:
        """
        Returns arguments that can be used to create new instances with the
        same initial values.

        Used by:

        * The :mod:`pickle` module for pickling.
        * The :mod:`copy` module for copying.

        The current state does not affect the arguments.

        Example:
            >>> orig = BinarySemaphore(0)
            >>> orig.initial_value
            0
            >>> copy = BinarySemaphore(*orig.__getnewargs__())
            >>> copy.initial_value
            0
        """

        return Semaphore.__getnewargs__(self)

    @copies(Semaphore.__getstate__)
    def __getstate__(self, /) -> None:
        """
        Disables the use of internal state for pickling and copying.
        """

        return Semaphore.__getstate__(self)

    @copies(Semaphore.__copy__)
    def __copy__(self, /) -> Self:
        """..."""

        return Semaphore.__copy__(self)

    @copies(Semaphore.__repr__)
    def __repr__(self, /) -> str:
        """..."""

        return Semaphore.__repr__(self)

    @copies(Semaphore.__aenter__)
    async def __aenter__(self, /) -> Self:
        """..."""

        return await Semaphore.__aenter__(self)

    @copies(Semaphore.__enter__)
    def __enter__(self, /) -> Self:
        """..."""

        return Semaphore.__enter__(self)

    @copies(Semaphore.__aexit__)
    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """..."""

        return await Semaphore.__aexit__(self, exc_type, exc_value, traceback)

    @copies(Semaphore.__exit__)
    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """..."""

        return Semaphore.__exit__(self, exc_type, exc_value, traceback)

    @copies(Semaphore.async_acquire)
    async def async_acquire(self, /, *, blocking: bool = True) -> bool:
        """..."""

        return await Semaphore.async_acquire(blocking=blocking)

    @copies(Semaphore.green_acquire)
    def green_acquire(
        self,
        /,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> bool:
        """..."""

        return Semaphore.green_acquire(blocking=blocking, timeout=timeout)

    def _release(self, /, count: int = 1) -> None:
        waiters = self._waiters

        while True:
            while waiters:
                try:
                    event = waiters.popleft()
                except IndexError:
                    break
                else:
                    if event.set():
                        return

            self._unlocked.append(None)

            if waiters:
                try:
                    self._unlocked.pop()
                except IndexError:
                    break
            else:
                break

    def release(self, /, count: int = 1) -> None:
        """..."""

        if count != 1:
            msg = "count must be 1"
            raise ValueError(msg)

        self._release(count)

    @copies(release)
    def async_release(self, /, count: int = 1) -> None:
        """..."""

        return self.release(count)

    @copies(release)
    def green_release(self, /, count: int = 1) -> None:
        """..."""

        return self.release(count)

    @property
    @copies(Semaphore.initial_value.fget)
    def initial_value(self, /) -> int:
        """
        The initial number of permits available for acquiring.
        """

        return Semaphore.initial_value.fget(self)

    @property
    @copies(Semaphore.value.fget)
    def value(self, /) -> int:
        """
        The current number of permits available to be acquired.

        It may not change after release if all the released permits have been
        reassigned to waiting tasks.
        """

        return Semaphore.value.fget(self)

    @property
    @copies(Semaphore.waiting.fget)
    def waiting(self, /) -> int:
        """
        The current number of tasks waiting to acquire.

        It represents the length of the waiting queue and thus changes
        immediately.
        """

        return Semaphore.waiting.fget(self)

    # Internal methods used by condition variables

    def _park(self, /, token: list[Any]) -> bool:
        event = token[0]

        if event.cancelled():
            return False

        self._waiters.append(event)

        token[5] = True  # reparked

        if event.cancelled():
            try:
                self._waiters.remove(event)
            except ValueError:
                pass

            return False

        return True

    def _unpark(self, /, event: Event) -> None:
        try:
            self._waiters.remove(event)
        except ValueError:
            pass

    def _after_park(self, /) -> None:
        pass


class BoundedBinarySemaphore(BinarySemaphore, BoundedSemaphore):
    """..."""

    __slots__ = ()

    def __new__(
        cls,
        /,
        initial_value: int | DefaultType = DEFAULT,
        max_value: int | DefaultType = DEFAULT,
    ) -> Self:
        """..."""

        self = object.__new__(cls)

        if initial_value is not DEFAULT:
            if initial_value < 0 or 1 < initial_value:
                msg = "initial_value must be 0 or 1"
                raise ValueError(msg)

            self._initial_value = initial_value
        elif max_value is not DEFAULT:
            self._initial_value = max_value
        else:
            self._initial_value = 1

        if max_value is not DEFAULT:
            if max_value < 0 or 1 < max_value:
                msg = "max_value must be 0 or 1"
                raise ValueError(msg)

            if max_value < self._initial_value:
                msg = "max_value must be >= initial_value"
                raise ValueError(msg)

            self._max_value = max_value
        else:
            self._max_value = self._initial_value

        if _USE_DELATTR:
            if self._max_value > self._initial_value:
                self._locked = True
        else:
            self._locked = [None] * (self._max_value - self._initial_value)

        self._unlocked = [None] * self._initial_value

        self._waiters = lazydeque()

        return self

    @copies(BoundedSemaphore.__getnewargs__)
    def __getnewargs__(self, /) -> tuple[Any, ...]:
        """
        Returns arguments that can be used to create new instances with the
        same initial values.

        Used by:

        * The :mod:`pickle` module for pickling.
        * The :mod:`copy` module for copying.

        The current state does not affect the arguments.

        Example:
            >>> orig = BoundedBinarySemaphore(0)
            >>> orig.max_value
            0
            >>> copy = BoundedBinarySemaphore(*orig.__getnewargs__())
            >>> copy.max_value
            0
        """

        return BoundedSemaphore.__getnewargs__(self)

    @copies(BoundedSemaphore.__getstate__)
    def __getstate__(self, /) -> None:
        """
        Disables the use of internal state for pickling and copying.
        """

        return BoundedSemaphore.__getstate__(self)

    @copies(BoundedSemaphore.__copy__)
    def __copy__(self, /) -> Self:
        """..."""

        return BoundedSemaphore.__copy__(self)

    @copies(BoundedSemaphore.__repr__)
    def __repr__(self, /) -> str:
        """..."""

        return BoundedSemaphore.__repr__(self)

    @copies(BinarySemaphore.__aenter__)
    async def __aenter__(self, /) -> Self:
        """..."""

        return await BinarySemaphore.__aenter__(self)

    @copies(BinarySemaphore.__enter__)
    def __enter__(self, /) -> Self:
        """..."""

        return BinarySemaphore.__enter__(self)

    @copies(BinarySemaphore.__aexit__)
    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """..."""

        return await BinarySemaphore.__aexit__(
            self,
            exc_type,
            exc_value,
            traceback,
        )

    @copies(BinarySemaphore.__exit__)
    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """..."""

        return BinarySemaphore.__exit__(self, exc_type, exc_value, traceback)

    async def async_acquire(self, /, *, blocking: bool = True) -> bool:
        """..."""

        success = await self._async_acquire(blocking=blocking)

        if success:
            if _USE_DELATTR:
                self._locked = True
            else:
                self._locked.append(None)

        return success

    def green_acquire(
        self,
        /,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> bool:
        """..."""

        success = self._green_acquire(blocking=blocking, timeout=timeout)

        if success:
            if _USE_DELATTR:
                self._locked = True
            else:
                self._locked.append(None)

        return success

    def release(self, /, count: int = 1) -> None:
        """..."""

        if count != 1:
            msg = "count must be 1"
            raise ValueError(msg)

        try:
            if _USE_DELATTR:
                del self._locked
            else:
                self._locked.pop()
        except (AttributeError, IndexError):
            msg = "semaphore released too many times"
            raise RuntimeError(msg) from None

        self._release(count)

    @copies(release)
    def async_release(self, /, count: int = 1) -> None:
        """..."""

        return self.release(count)

    @copies(release)
    def green_release(self, /, count: int = 1) -> None:
        """..."""

        return self.release(count)

    @property
    @copies(BinarySemaphore.initial_value.fget)
    def initial_value(self, /) -> int:
        """
        The initial number of permits available for acquiring.
        """

        return BinarySemaphore.initial_value.fget(self)

    @property
    @copies(BoundedSemaphore.max_value.fget)
    def max_value(self, /) -> int:
        """
        The maximum number of permits which the semaphore can hold.
        """

        return BoundedSemaphore.max_value.fget(self)

    @property
    @copies(BinarySemaphore.value.fget)
    def value(self, /) -> int:
        """
        The current number of permits available to be acquired.

        It may not change after release if all the released permits have been
        reassigned to waiting tasks.
        """

        return BinarySemaphore.value.fget(self)

    @property
    @copies(BinarySemaphore.waiting.fget)
    def waiting(self, /) -> int:
        """
        The current number of tasks waiting to acquire.

        It represents the length of the waiting queue and thus changes
        immediately.
        """

        return BinarySemaphore.waiting.fget(self)

    # Internal methods used by condition variables

    def _after_park(self, /) -> None:
        if _USE_DELATTR:
            self._locked = True
        else:
            self._locked.append(None)
