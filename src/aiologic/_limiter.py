#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

from types import MappingProxyType, TracebackType
from typing import TYPE_CHECKING, Any

from ._semaphore import BinarySemaphore, Semaphore
from .lowlevel import (
    async_checkpoint,
    current_async_task_ident,
    current_green_task_ident,
    green_checkpoint,
)
from .meta import DEFAULT, DefaultType, copies

if TYPE_CHECKING:
    import sys

    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self


class CapacityLimiter:
    """..."""

    __slots__ = (
        "__weakref__",
        "_borrowers",
        "_borrowers_proxy",
        "_semaphore",
    )

    def __new__(cls, /, total_tokens: int | DefaultType = DEFAULT) -> Self:
        """..."""

        if total_tokens is DEFAULT:
            total_tokens = 1
        elif total_tokens < 0:
            msg = "total_tokens must be >= 0"
            raise ValueError(msg)

        self = object.__new__(cls)

        self._borrowers = {}
        self._borrowers_proxy = MappingProxyType(self._borrowers)

        if total_tokens >= 2:
            self._semaphore = Semaphore(total_tokens)
        else:
            self._semaphore = BinarySemaphore(total_tokens)

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
            >>> orig = CapacityLimiter(3)
            >>> orig.total_tokens
            3
            >>> copy = CapacityLimiter(*orig.__getnewargs__())
            >>> copy.total_tokens
            3
        """

        return (self._semaphore.initial_value,)

    def __getstate__(self, /) -> None:
        """
        Disables the use of internal state for pickling and copying.
        """

        return None

    def __copy__(self, /) -> Self:
        """..."""

        return self.__class__(self._semaphore.initial_value)

    def __repr__(self, /) -> str:
        """..."""

        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        object_repr = f"{cls_repr}({self._semaphore.initial_value!r})"

        available_tokens = self._semaphore.value

        if available_tokens > 0:
            extra = f"available_tokens={available_tokens}"
        else:
            waiting = self._semaphore.waiting

            extra = f"available_tokens={available_tokens}, waiting={waiting}"

        return f"<{object_repr} at {id(self):#x} [{extra}]>"

    def __bool__(self, /) -> bool:
        """
        Returns :data:`True` if the capacity limiter is used by any task.

        Used by the standard :ref:`truth testing procedure <truth>`.

        Example:
            >>> reading = CapacityLimiter()
            >>> bool(reading)
            False
            >>> with reading:  # capacity limiter is in use
            ...     bool(reading)
            True
            >>> bool(reading)
            False
        """

        return self._semaphore.initial_value > self._semaphore.value

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

    async def async_acquire(self, /, *, blocking: bool = True) -> bool:
        """..."""

        task = current_async_task_ident()

        if task in self._borrowers:
            msg = (
                "the current task is already holding"
                " one of this capacity limiter's tokens",
            )
            raise RuntimeError(msg)

        success = await self._semaphore.async_acquire(blocking=blocking)

        if success:
            self._borrowers[task] = 1

        return success

    def green_acquire(
        self,
        /,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> bool:
        """..."""

        task = current_green_task_ident()

        if task in self._borrowers:
            msg = (
                "the current task is already holding"
                " one of this capacity limiter's tokens",
            )
            raise RuntimeError(msg)

        success = self._semaphore.green_acquire(
            blocking=blocking,
            timeout=timeout,
        )

        if success:
            self._borrowers[task] = 1

        return success

    def async_release(self, /) -> None:
        """..."""

        task = current_async_task_ident()

        try:
            del self._borrowers[task]
        except KeyError:
            msg = (
                "the current task is not holding"
                " any of this capacity limiter's tokens"
            )
            raise RuntimeError(msg) from None

        self._semaphore.async_release()

    def green_release(self, /) -> None:
        """..."""

        task = current_green_task_ident()

        try:
            del self._borrowers[task]
        except KeyError:
            msg = (
                "the current task is not holding"
                " any of this capacity limiter's tokens"
            )
            raise RuntimeError(msg) from None

        self._semaphore.green_release()

    def async_borrowed(self, /) -> bool:
        """
        Return :data:`True` if the current async task holds any token.

        Example:
            >>> limiter = CapacityLimiter()
            >>> limiter.async_borrowed()
            False
            >>> async with limiter:
            ...     limiter.async_borrowed()
            True
            >>> limiter.async_borrowed()
            False
        """

        return current_async_task_ident() in self._borrowers

    def green_borrowed(self, /) -> bool:
        """
        Return :data:`True` if the current green task holds any token.

        Example:
            >>> limiter = CapacityLimiter()
            >>> limiter.green_borrowed()
            False
            >>> with limiter:
            ...     limiter.green_borrowed()
            True
            >>> limiter.green_borrowed()
            False
        """

        return current_green_task_ident() in self._borrowers

    @property
    def total_tokens(self, /) -> int:
        """
        The initial number of tokens available for borrowing.
        """

        return self._semaphore.initial_value

    @property
    def available_tokens(self, /) -> int:
        """
        The current number of tokens available to be borrowed.

        It may not change after release if all the released tokens have been
        reassigned to waiting tasks.
        """

        return self._semaphore.value

    @property
    def borrowed_tokens(self, /) -> int:
        """
        The current number of tokens that have been borrowed.

        It may not change after release if all the released tokens have been
        reassigned to waiting tasks.
        """

        return self._semaphore.initial_value - self._semaphore.value

    @property
    def borrowers(self, /) -> MappingProxyType[tuple[str, int], int]:
        """
        The read-only proxy of the dictionary that maps tasks' identifiers to
        their respective recursion levels. Contains identifiers of only those
        tasks that hold any token. Updated automatically when the current state
        changes.

        It may not contain identifiers of those tasks to which tokens were
        reassigned during release if they have not yet resumed execution.
        """

        return self._borrowers_proxy

    @property
    def waiting(self, /) -> int:
        """
        The current number of tasks waiting to borrow.

        It represents the length of the waiting queue and thus changes
        immediately.
        """

        return self._semaphore.waiting


class RCapacityLimiter(CapacityLimiter):
    """..."""

    __slots__ = ()

    @copies(CapacityLimiter.__new__)
    def __new__(cls, /, total_tokens: int | DefaultType = DEFAULT) -> Self:
        """..."""

        return CapacityLimiter.__new__(cls, total_tokens)

    @copies(CapacityLimiter.__getnewargs__)
    def __getnewargs__(self, /) -> tuple[Any, ...]:
        """
        Returns arguments that can be used to create new instances with the
        same initial values.

        Used by:

        * The :mod:`pickle` module for pickling.
        * The :mod:`copy` module for copying.

        The current state does not affect the arguments.

        Example:
            >>> orig = RCapacityLimiter(3)
            >>> orig.total_tokens
            3
            >>> copy = RCapacityLimiter(*orig.__getnewargs__())
            >>> copy.total_tokens
            3
        """

        return CapacityLimiter.__getnewargs__(self)

    @copies(CapacityLimiter.__getstate__)
    def __getstate__(self, /) -> None:
        """
        Disables the use of internal state for pickling and copying.
        """

        return CapacityLimiter.__getstate__(self)

    @copies(CapacityLimiter.__copy__)
    def __copy__(self, /) -> Self:
        """..."""

        return CapacityLimiter.__copy__(self)

    @copies(CapacityLimiter.__repr__)
    def __repr__(self, /) -> str:
        """..."""

        return CapacityLimiter.__repr__(self)

    @copies(CapacityLimiter.__bool__)
    def __bool__(self, /) -> bool:
        """
        Returns :data:`True` if the capacity limiter is used by any task.

        Used by the standard :ref:`truth testing procedure <truth>`.

        Example:
            >>> reading = RCapacityLimiter()
            >>> bool(reading)
            False
            >>> with reading:  # capacity limiter is in use
            ...     bool(reading)
            True
            >>> bool(reading)
            False
        """

        return CapacityLimiter.__bool__(self)

    @copies(CapacityLimiter.__aenter__)
    async def __aenter__(self, /) -> Self:
        """..."""

        return await CapacityLimiter.__aenter__(self)

    @copies(CapacityLimiter.__enter__)
    def __enter__(self, /) -> Self:
        """..."""

        return CapacityLimiter.__enter__(self)

    @copies(CapacityLimiter.__aexit__)
    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """..."""

        return await CapacityLimiter.__aexit__(
            self,
            exc_type,
            exc_value,
            traceback,
        )

    @copies(CapacityLimiter.__exit__)
    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """..."""

        return CapacityLimiter.__exit__(self, exc_type, exc_value, traceback)

    async def async_acquire(
        self,
        /,
        count: int = 1,
        *,
        blocking: bool = True,
    ) -> bool:
        """..."""

        if count < 1:
            msg = "count must be >= 1"
            raise ValueError(msg)

        task = current_async_task_ident()

        try:
            current_count = self._borrowers[task]
        except KeyError:
            pass
        else:
            if blocking:
                await async_checkpoint()

            self._borrowers[task] = current_count + count

            return True

        success = await self._semaphore.async_acquire(blocking=blocking)

        if success:
            self._borrowers[task] = count

        return success

    def green_acquire(
        self,
        /,
        count: int = 1,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> bool:
        """..."""

        if count < 1:
            msg = "count must be >= 1"
            raise ValueError(msg)

        task = current_green_task_ident()

        try:
            current_count = self._borrowers[task]
        except KeyError:
            pass
        else:
            if blocking:
                green_checkpoint()

            self._borrowers[task] = current_count + count

            return True

        success = self._semaphore.green_acquire(
            blocking=blocking,
            timeout=timeout,
        )

        if success:
            self._borrowers[task] = count

        return success

    def async_release(self, /, count: int = 1) -> None:
        """..."""

        if count < 1:
            msg = "count must be >= 1"
            raise ValueError(msg)

        task = current_async_task_ident()

        try:
            current_count = self._borrowers[task]
        except KeyError:
            msg = (
                "the current task is not holding"
                " any of this capacity limiter's tokens"
            )
            raise RuntimeError(msg) from None

        if current_count > count:
            self._borrowers[task] = current_count - count
        elif current_count == count:
            del self._borrowers[task]

            self._semaphore.async_release()
        else:
            msg = "capacity limiter released too many times"
            raise RuntimeError(msg)

    def green_release(self, /, count: int = 1) -> None:
        """..."""

        if count < 1:
            msg = "count must be >= 1"
            raise ValueError(msg)

        task = current_green_task_ident()

        try:
            current_count = self._borrowers[task]
        except KeyError:
            msg = (
                "the current task is not holding"
                " any of this capacity limiter's tokens"
            )
            raise RuntimeError(msg) from None

        if current_count > count:
            self._borrowers[task] = current_count - count
        elif current_count == count:
            del self._borrowers[task]

            self._semaphore.green_release()
        else:
            msg = "capacity limiter released too many times"
            raise RuntimeError(msg)

    @copies(CapacityLimiter.async_borrowed)
    def async_borrowed(self, /) -> bool:
        """
        Return :data:`True` if the current async task holds any token.

        Example:
            >>> limiter = RCapacityLimiter()
            >>> limiter.async_borrowed()
            False
            >>> async with limiter:
            ...     limiter.async_borrowed()
            True
            >>> limiter.async_borrowed()
            False
        """

        return CapacityLimiter.async_borrowed(self)

    @copies(CapacityLimiter.green_borrowed)
    def green_borrowed(self, /) -> bool:
        """
        Return :data:`True` if the current green task holds any token.

        Example:
            >>> limiter = RCapacityLimiter()
            >>> limiter.green_borrowed()
            False
            >>> with limiter:
            ...     limiter.green_borrowed()
            True
            >>> limiter.green_borrowed()
            False
        """

        return CapacityLimiter.green_borrowed(self)

    def async_count(self, /) -> int:
        """
        Return the recursion level of the current async task.

        Example:
            >>> limiter = RCapacityLimiter()
            >>> limiter.async_count()
            0
            >>> async with limiter:
            ...     limiter.async_count()
            1
            >>> limiter.async_count()
            0
        """

        return self._borrowers.get(current_async_task_ident(), 0)

    def green_count(self, /) -> int:
        """
        Return the recursion level of the current green task.

        Example:
            >>> limiter = RCapacityLimiter()
            >>> limiter.green_count()
            0
            >>> with limiter:
            ...     limiter.green_count()
            1
            >>> limiter.green_count()
            0
        """

        return self._borrowers.get(current_green_task_ident(), 0)

    @property
    @copies(CapacityLimiter.total_tokens.fget)
    def total_tokens(self, /) -> int:
        """
        The initial number of tokens available for borrowing.
        """

        return CapacityLimiter.total_tokens.fget(self)

    @property
    @copies(CapacityLimiter.available_tokens.fget)
    def available_tokens(self, /) -> int:
        """
        The current number of tokens available to be borrowed.

        It may not change after release if all the released tokens have been
        reassigned to waiting tasks.
        """

        return CapacityLimiter.available_tokens.fget(self)

    @property
    @copies(CapacityLimiter.borrowed_tokens.fget)
    def borrowed_tokens(self, /) -> int:
        """
        The current number of tokens that have been borrowed.

        It may not change after release if all the released tokens have been
        reassigned to waiting tasks.
        """

        return CapacityLimiter.borrowed_tokens.fget(self)

    @property
    @copies(CapacityLimiter.borrowers.fget)
    def borrowers(self, /) -> MappingProxyType[tuple[str, int], int]:
        """
        The read-only proxy of the dictionary that maps tasks' identifiers to
        their respective recursion levels. Contains identifiers of only those
        tasks that hold any token. Updated automatically when the current state
        changes.

        It may not contain identifiers of those tasks to which tokens were
        reassigned during release if they have not yet resumed execution.
        """

        return CapacityLimiter.borrowers.fget(self)

    @property
    @copies(CapacityLimiter.waiting.fget)
    def waiting(self, /) -> int:
        """
        The current number of tasks waiting to borrow.

        It represents the length of the waiting queue and thus changes
        immediately.
        """

        return CapacityLimiter.waiting.fget(self)
