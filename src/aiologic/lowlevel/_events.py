#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from abc import ABC, abstractmethod
from typing import Any, Final, Literal, NoReturn, Protocol, final

from aiologic.meta import copies, generator

from ._checkpoints import async_checkpoint, green_checkpoint
from ._locks import ThreadOnceLock
from ._waiters import create_async_waiter, create_green_waiter

try:
    from sys import _is_gil_enabled
except ImportError:
    __GIL_ENABLED: Final[bool] = True
else:
    __GIL_ENABLED: Final[bool] = _is_gil_enabled()

_USE_DELATTR: Final[bool] = (
    __GIL_ENABLED or sys.version_info >= (3, 14)  # see python/cpython#146270
)


class Event(Protocol):
    """..."""

    __slots__ = ()

    def __bool__(self, /) -> bool:
        """..."""

    def set(self, /) -> bool:
        """..."""

    def is_set(self, /) -> bool:
        """..."""

    def cancelled(self, /) -> bool:
        """..."""

    @property
    def shield(self, /) -> bool:
        """..."""

    @shield.setter
    def shield(self, /, value: bool) -> None: ...

    @property
    def force(self, /) -> bool:
        """..."""

    @force.setter
    def force(self, /, value: bool) -> None: ...


class GreenEvent(ABC, Event):
    """
    The return type of :func:`create_green_waiter`.
    """

    __slots__ = ()

    @abstractmethod
    def wait(self, /, timeout: float | None = None) -> bool:
        """
        Block (put to sleep) the task until :meth:`set` is called from any
        thread, and then return :data:`True`.

        It must be called exactly once (or never) during the object's lifetime,
        even if the first call was cancelled due to a timeout. Otherwise, a
        :exc:`RuntimeError` is raised.

        If the event is already in the set state (and the method has not yet
        been called), this is equivalent to :func:`green_checkpoint`.

        Args:
          timeout:
            If set to a non-negative number, the method will block at most
            *timeout* seconds and return :data:`False` if there were no calls
            to :meth:`set` within that time. For zero: if no such calls were
            serialized.
        """

        raise NotImplementedError

    @abstractmethod
    def __bool__(self, /) -> bool:
        """
        Return :data:`True` if the :meth:`set` method was successfully called,
        :data:`False` otherwise. Mutually exclusive with :meth:`cancelled`.

        It is reliable only after the task has been rescheduled (that is,
        primarily for checks on the task's own side). Attempts at parallel
        checks from notifiers may return false values (situations where the
        :meth:`set` method has already been called by someone else, but both
        :meth:`is_set` and :meth:`cancelled` return :data:`False`; the same
        applies to races between the task and one notifier when the former is
        cancelled).

        Used by the standard :ref:`truth testing procedure <truth>`.
        """

        return self.is_set()

    @abstractmethod
    def set(self, /) -> bool:
        """
        Put the event into the set state, and return :data:`True` if this was
        the first successful attempt (no one preempted it, and the call to the
        :meth:`wait` method was not cancelled), :data:`False` otherwise.

        If the task is already blocked, it is rescheduled. Otherwise, the
        subsequent call will behave only as a checkpoint (no actual waiting).
        """

        raise NotImplementedError

    @abstractmethod
    def is_set(self, /) -> bool:
        """
        Return :data:`True` if the :meth:`set` method was successfully called,
        :data:`False` otherwise. Mutually exclusive with :meth:`cancelled`.

        It is reliable only after the task has been rescheduled (that is,
        primarily for checks on the task's own side). Attempts at parallel
        checks from notifiers may return false values (situations where the
        :meth:`set` method has already been called by someone else, but both
        :meth:`is_set` and :meth:`cancelled` return :data:`False`; the same
        applies to races between the task and one notifier when the former is
        cancelled).
        """

        raise NotImplementedError

    @abstractmethod
    def cancelled(self, /) -> bool:
        """
        Return :data:`True` if the call was cancelled (interrupted by a timeout
        or any exception), :data:`False` otherwise. Mutually exclusive with
        :meth:`is_set`.

        It is reliable only after the task has been rescheduled (that is,
        primarily for checks on the task's own side). Attempts at parallel
        checks from notifiers may return false values (situations where the
        :meth:`set` method has already been called by someone else, but both
        :meth:`is_set` and :meth:`cancelled` return :data:`False`; the same
        applies to races between the task and one notifier when the former is
        cancelled).
        """

        raise NotImplementedError

    @property
    @abstractmethod
    def shield(self, /) -> bool:
        """
        A boolean that is :data:`True` if the :meth:`wait` call will be
        shielded from external cancellation, :data:`False` otherwise.

        The effect is mostly equivalent to applying the :func:`shield`
        universal decorator to the method, but it is more efficient. Also, any
        non-negative timeout passed to the method will be ignored.

        It can be rewritten, but any changes will only take effect until the
        call.
        """

        raise NotImplementedError

    @shield.setter
    @abstractmethod
    def shield(self, /, value: bool) -> None:
        raise NotImplementedError

    @property
    @abstractmethod
    def force(self, /) -> bool:
        """
        A boolean that is :data:`True` if the :meth:`wait` call will have a
        forced checkpoint (that is, the call is guaranteed to switch to the
        event loop and check for cancellation), :data:`False` otherwise.

        The effect is mostly equivalent to applying the
        :func:`enable_checkpoints` universal decorator to the method, but it is
        more efficient.

        It can be rewritten, but any changes will only take effect until the
        call.
        """

        raise NotImplementedError

    @force.setter
    @abstractmethod
    def force(self, /, value: bool) -> None:
        raise NotImplementedError


class AsyncEvent(ABC, Event):
    """
    The return type of :func:`create_async_waiter`.
    """

    __slots__ = ()

    @abstractmethod
    @generator
    async def __await__(self, /, timeout: float | None = None) -> bool:
        """
        Block (put to sleep) the task until :meth:`set` is called from any
        thread, and then return :data:`True`.

        It must be called exactly once (or never) during the object's lifetime,
        even if the first call was cancelled due to a timeout. Otherwise, a
        :exc:`RuntimeError` is raised.

        If the event is already in the set state (and the method has not yet
        been called), this is equivalent to :func:`async_checkpoint`.

        Args:
          timeout:
            If set to a non-negative number, the method will block at most
            *timeout* seconds and return :data:`False` if there were no calls
            to :meth:`set` within that time. For zero: if no such calls were
            serialized.
        """

        raise NotImplementedError

    @abstractmethod
    async def with_(self, /, timeout: float | None = None) -> bool:
        """
        Block (put to sleep) the task until :meth:`set` is called from any
        thread, and then return :data:`True`.

        It must be called exactly once (or never) during the object's lifetime,
        even if the first call was cancelled due to a timeout. Otherwise, a
        :exc:`RuntimeError` is raised.

        If the event is already in the set state (and the method has not yet
        been called), this is equivalent to :func:`async_checkpoint`.

        Args:
          timeout:
            If set to a non-negative number, the method will block at most
            *timeout* seconds and return :data:`False` if there were no calls
            to :meth:`set` within that time. For zero: if no such calls were
            serialized.
        """

        raise NotImplementedError

    @abstractmethod
    def __bool__(self, /) -> bool:
        """
        Return :data:`True` if the :meth:`set` method was successfully called,
        :data:`False` otherwise. Mutually exclusive with :meth:`cancelled`.

        It is reliable only after the task has been rescheduled (that is,
        primarily for checks on the task's own side). Attempts at parallel
        checks from notifiers may return false values (situations where the
        :meth:`set` method has already been called by someone else, but both
        :meth:`is_set` and :meth:`cancelled` return :data:`False`; the same
        applies to races between the task and one notifier when the former is
        cancelled).

        Used by the standard :ref:`truth testing procedure <truth>`.
        """

        return self.is_set()

    @abstractmethod
    def set(self, /) -> bool:
        """
        Put the event into the set state, and return :data:`True` if this was
        the first successful attempt (no one preempted it, and the call to the
        :meth:`__await__`/:meth:`with_` method was not cancelled),
        :data:`False` otherwise.

        If the task is already blocked, it is rescheduled. Otherwise, the
        subsequent call will behave only as a checkpoint (no actual waiting).
        """

        raise NotImplementedError

    @abstractmethod
    def is_set(self, /) -> bool:
        """
        Return :data:`True` if the :meth:`set` method was successfully called,
        :data:`False` otherwise. Mutually exclusive with :meth:`cancelled`.

        It is reliable only after the task has been rescheduled (that is,
        primarily for checks on the task's own side). Attempts at parallel
        checks from notifiers may return false values (situations where the
        :meth:`set` method has already been called by someone else, but both
        :meth:`is_set` and :meth:`cancelled` return :data:`False`; the same
        applies to races between the task and one notifier when the former is
        cancelled).
        """

        raise NotImplementedError

    @abstractmethod
    def cancelled(self, /) -> bool:
        """
        Return :data:`True` if the call was cancelled (interrupted by a timeout
        or any exception), :data:`False` otherwise. Mutually exclusive with
        :meth:`is_set`.

        It is reliable only after the task has been rescheduled (that is,
        primarily for checks on the task's own side). Attempts at parallel
        checks from notifiers may return false values (situations where the
        :meth:`set` method has already been called by someone else, but both
        :meth:`is_set` and :meth:`cancelled` return :data:`False`; the same
        applies to races between the task and one notifier when the former is
        cancelled).
        """

        raise NotImplementedError

    @property
    @abstractmethod
    def shield(self, /) -> bool:
        """
        A boolean that is :data:`True` if the :meth:`__await__`/:meth:`with_`
        call will be shielded from external cancellation, :data:`False`
        otherwise.

        The effect is mostly equivalent to applying the :func:`shield`
        universal decorator to the primitive/method, but it is more efficient.
        Also, any non-negative timeout passed to the method will be ignored.

        It can be rewritten, but any changes will only take effect until the
        call.
        """

        raise NotImplementedError

    @shield.setter
    @abstractmethod
    def shield(self, /, value: bool) -> None:
        raise NotImplementedError

    @property
    @abstractmethod
    def force(self, /) -> bool:
        """
        A boolean that is :data:`True` if the :meth:`__await__`/:meth:`with_`
        call will have a forced checkpoint (that is, the call is guaranteed to
        switch to the event loop and check for cancellation), :data:`False`
        otherwise.

        The effect is mostly equivalent to applying the
        :func:`enable_checkpoints` universal decorator to the primitive/method,
        but it is more efficient.

        It can be rewritten, but any changes will only take effect until the
        call.
        """

        raise NotImplementedError

    @force.setter
    @abstractmethod
    def force(self, /, value: bool) -> None:
        raise NotImplementedError


@final
class SetEvent(GreenEvent, AsyncEvent):
    """
    The singleton type for :data:`SET_EVENT`.
    """

    __slots__ = ()

    def __new__(cls, /) -> SetEvent:
        return SET_EVENT

    def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn:
        bcs = SetEvent
        bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

        msg = f"type '{bcs_repr}' is not an acceptable base type"
        raise TypeError(msg)

    def __reduce__(self, /) -> str:
        return "SET_EVENT"

    def __copy__(self, /) -> SetEvent:
        return SET_EVENT

    def __repr__(self, /) -> str:
        return f"{self.__class__.__module__}.SET_EVENT"

    def __bool__(self, /) -> Literal[True]:
        return True

    async def __await(self, /, timeout: float | None = None) -> Literal[True]:
        await async_checkpoint()

        return True

    @generator
    @copies(__await)
    async def __await__(
        self,
        /,
        timeout: float | None = None,
    ) -> Literal[True]:
        return await self.__await(timeout)

    @copies(__await)
    async def with_(self, /, timeout: float | None = None) -> Literal[True]:
        return await self.__await(timeout)

    def wait(self, /, timeout: float | None = None) -> Literal[True]:
        green_checkpoint()

        return True

    def set(self, /) -> Literal[False]:
        return False

    def is_set(self, /) -> Literal[True]:
        return True

    def cancelled(self, /) -> Literal[False]:
        return False

    @property
    def shield(self, /) -> bool:
        return False

    @shield.setter
    def shield(self, /, value: bool) -> NoReturn:
        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        msg = f"'{cls_repr}' object attribute 'shield' is read-only"
        raise AttributeError(msg)

    @property
    def force(self, /) -> bool:
        return False

    @force.setter
    def force(self, /, value: bool) -> NoReturn:
        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        msg = f"'{cls_repr}' object attribute 'force' is read-only"
        raise AttributeError(msg)


@final
class DummyEvent(GreenEvent, AsyncEvent):
    """
    The singleton type for :data:`DUMMY_EVENT`.
    """

    __slots__ = ()

    def __new__(cls, /) -> DummyEvent:
        return DUMMY_EVENT

    def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn:
        bcs = DummyEvent
        bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

        msg = f"type '{bcs_repr}' is not an acceptable base type"
        raise TypeError(msg)

    def __reduce__(self, /) -> str:
        return "DUMMY_EVENT"

    def __copy__(self, /) -> DummyEvent:
        return DUMMY_EVENT

    def __repr__(self, /) -> str:
        return f"{self.__class__.__module__}.DUMMY_EVENT"

    def __bool__(self, /) -> Literal[True]:
        return True

    async def __await(self, /, timeout: float | None = None) -> Literal[True]:
        await async_checkpoint()

        return True

    @generator
    @copies(__await)
    async def __await__(
        self,
        /,
        timeout: float | None = None,
    ) -> Literal[True]:
        return await self.__await(timeout)

    @copies(__await)
    async def with_(self, /, timeout: float | None = None) -> Literal[True]:
        return await self.__await(timeout)

    def wait(self, /, timeout: float | None = None) -> Literal[True]:
        green_checkpoint()

        return True

    def set(self, /) -> Literal[False]:
        return False

    def is_set(self, /) -> Literal[True]:
        return True

    def cancelled(self, /) -> Literal[False]:
        return False

    @property
    def shield(self, /) -> bool:
        return False

    @shield.setter
    def shield(self, /, value: bool) -> NoReturn:
        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        msg = f"'{cls_repr}' object attribute 'shield' is read-only"
        raise AttributeError(msg)

    @property
    def force(self, /) -> bool:
        return False

    @force.setter
    def force(self, /, value: bool) -> NoReturn:
        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        msg = f"'{cls_repr}' object attribute 'force' is read-only"
        raise AttributeError(msg)


@final
class CancelledEvent(GreenEvent, AsyncEvent):
    """
    The singleton type for :data:`CANCELLED_EVENT`.
    """

    __slots__ = ()

    def __new__(cls, /) -> CancelledEvent:
        return CANCELLED_EVENT

    def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn:
        bcs = CancelledEvent
        bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

        msg = f"type '{bcs_repr}' is not an acceptable base type"
        raise TypeError(msg)

    def __reduce__(self, /) -> str:
        return "CANCELLED_EVENT"

    def __copy__(self, /) -> CancelledEvent:
        return CANCELLED_EVENT

    def __repr__(self, /) -> str:
        return f"{self.__class__.__module__}.CANCELLED_EVENT"

    def __bool__(self, /) -> Literal[False]:
        return False

    async def __await(self, /, timeout: float | None = None) -> Literal[False]:
        await async_checkpoint()

        return False

    @generator
    @copies(__await)
    async def __await__(
        self,
        /,
        timeout: float | None = None,
    ) -> Literal[False]:
        return await self.__await(timeout)

    @copies(__await)
    async def with_(self, /, timeout: float | None = None) -> Literal[False]:
        return await self.__await(timeout)

    def wait(self, /, timeout: float | None = None) -> Literal[False]:
        green_checkpoint()

        return False

    def set(self, /) -> Literal[False]:
        return False

    def is_set(self, /) -> Literal[False]:
        return False

    def cancelled(self, /) -> Literal[True]:
        return True

    @property
    def shield(self, /) -> bool:
        return False

    @shield.setter
    def shield(self, /, value: bool) -> NoReturn:
        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        msg = f"'{cls_repr}' object attribute 'shield' is read-only"
        raise AttributeError(msg)

    @property
    def force(self, /) -> bool:
        return False

    @force.setter
    def force(self, /, value: bool) -> NoReturn:
        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        msg = f"'{cls_repr}' object attribute 'force' is read-only"
        raise AttributeError(msg)


SET_EVENT: Final[SetEvent] = object.__new__(SetEvent)
DUMMY_EVENT: Final[DummyEvent] = object.__new__(DummyEvent)
CANCELLED_EVENT: Final[CancelledEvent] = object.__new__(CancelledEvent)


class _BaseEvent(ABC, Event):
    __slots__ = (
        "_is_cancelled",
        "_is_pending",
        "_is_set",
        "_is_unset",
        "_waiter",
        "force",
        "shield",
    )

    force: bool
    shield: bool

    def __init__(self, /, shield: bool = False, force: bool = False) -> None:
        self._is_cancelled = False

        if _USE_DELATTR:
            self._is_pending = True
        else:
            self._is_pending = [True]

        self._is_set = False

        if _USE_DELATTR:
            self._is_unset = True
        else:
            self._is_unset = [True]

        self._waiter = None

        self.force = force
        self.shield = shield

    def __bool__(self, /) -> bool:
        return self._is_set

    def set(self, /) -> bool:
        if self._is_set or self._is_cancelled:
            return False

        try:
            if _USE_DELATTR:
                del self._is_unset
            else:
                self._is_unset.pop()
        except (AttributeError, IndexError):
            return False

        self._is_set = True

        if (waiter := self._waiter) is not None:
            waiter.wake()

        return True

    def is_set(self, /) -> bool:
        return self._is_set

    def cancelled(self, /) -> bool:
        return self._is_cancelled


class _GreenEventImpl(_BaseEvent, GreenEvent):
    __slots__ = ()

    __new__ = _BaseEvent.__new__

    def __reduce__(self, /) -> NoReturn:
        msg = f"cannot reduce {self!r}"
        raise TypeError(msg)

    def __repr__(self, /) -> str:
        cls_repr = f"{GreenEvent.__module__}.GreenEvent"

        if self._is_set:
            state = "set"
        elif self._is_cancelled:
            state = "cancelled"
        else:
            state = "unset"

        return f"<{cls_repr} object at {id(self):#x}: {state}>"

    def wait(self, /, timeout: float | None = None) -> bool:
        if self._is_set:
            green_checkpoint(force=self.force)

            return True

        if self._is_cancelled:
            green_checkpoint(force=self.force)

            return False

        try:
            if _USE_DELATTR:
                del self._is_pending
            else:
                self._is_pending.pop()
        except (AttributeError, IndexError):
            msg = "this event is already in use"
            raise RuntimeError(msg) from None

        self._waiter = create_green_waiter(shield=self.shield)

        try:
            if self._is_set:
                green_checkpoint(force=self.force)

                return True

            try:
                return self._waiter.wait(timeout)
            finally:
                if not self._is_set:
                    try:
                        if _USE_DELATTR:
                            del self._is_unset
                        else:
                            self._is_unset.pop()
                    except (AttributeError, IndexError):
                        self._is_set = True
                    else:
                        self._is_cancelled = True
        finally:
            self._waiter = None


class _AsyncEventImpl(_BaseEvent, AsyncEvent):
    __slots__ = ()

    __new__ = _BaseEvent.__new__

    def __reduce__(self, /) -> NoReturn:
        msg = f"cannot reduce {self!r}"
        raise TypeError(msg)

    def __repr__(self, /) -> str:
        cls_repr = f"{AsyncEvent.__module__}.AsyncEvent"

        if self._is_set:
            state = "set"
        elif self._is_cancelled:
            state = "cancelled"
        else:
            state = "unset"

        return f"<{cls_repr} object at {id(self):#x}: {state}>"

    async def __await(self, /, timeout: float | None = None) -> bool:
        if self._is_set:
            await async_checkpoint(force=self.force)

            return True

        if self._is_cancelled:
            await async_checkpoint(force=self.force)

            return False

        try:
            if _USE_DELATTR:
                del self._is_pending
            else:
                self._is_pending.pop()
        except (AttributeError, IndexError):
            msg = "this event is already in use"
            raise RuntimeError(msg) from None

        self._waiter = create_async_waiter(shield=self.shield)

        try:
            if self._is_set:
                await async_checkpoint(force=self.force)

                return True

            try:
                return await self._waiter.with_(timeout)
            finally:
                if not self._is_set:
                    try:
                        if _USE_DELATTR:
                            del self._is_unset
                        else:
                            self._is_unset.pop()
                    except (AttributeError, IndexError):
                        self._is_set = True
                    else:
                        self._is_cancelled = True
        finally:
            self._waiter = None

    @generator
    @copies(__await)
    async def __await__(self, /, timeout: float | None = None) -> bool:
        return await self.__await(timeout)

    @copies(__await)
    async def with_(self, /, timeout: float | None = None) -> bool:
        return await self.__await(timeout)


class __LockingGreenEventImpl(_GreenEventImpl):
    __slots__ = tuple(
        name for name in ThreadOnceLock.__slots__ if name != "__weakref__"
    )


class __LockingAsyncEventImpl(_AsyncEventImpl):
    __slots__ = tuple(
        name for name in ThreadOnceLock.__slots__ if name != "__weakref__"
    )


def create_green_event(
    *,
    locking: bool = False,
    shield: bool = False,
    force: bool = False,
) -> GreenEvent:
    """
    Create a new instance for a blocking green call (with state).

    Args:
      locking:
        If set to :data:`True`, the instance will also include the slots of
        :class:`ThreadOnceLock`, allowing the latter's methods to be used with
        the returned object. This can be used when one-time synchronization on
        the event is required, but having a separate :class:`ThreadOnceLock`
        instance is expensive in terms of memory.
      shield:
        See the :attr:`~GreenEvent.shield` property.
      force:
        See the :attr:`~GreenEvent.force` property.
    """

    if locking:
        event = __LockingGreenEventImpl(shield, force)
    else:
        event = _GreenEventImpl(shield, force)

    if locking:
        ThreadOnceLock.__init__(event)

    return event


def create_async_event(
    *,
    locking: bool = False,
    shield: bool = False,
    force: bool = False,
) -> AsyncEvent:
    """
    Create a new instance for a blocking async call (with state).

    Args:
      locking:
        If set to :data:`True`, the instance will also include the slots of
        :class:`ThreadOnceLock`, allowing the latter's methods to be used with
        the returned object. This can be used when one-time synchronization on
        the event is required, but having a separate :class:`ThreadOnceLock`
        instance is expensive in terms of memory.
      shield:
        See the :attr:`~AsyncEvent.shield` property.
      force:
        See the :attr:`~AsyncEvent.force` property.
    """

    if locking:
        event = __LockingAsyncEventImpl(shield, force)
    else:
        event = _AsyncEventImpl(shield, force)

    if locking:
        ThreadOnceLock.__init__(event)

    return event
