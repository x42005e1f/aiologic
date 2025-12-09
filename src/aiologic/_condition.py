#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from collections import defaultdict
from itertools import count
from logging import Logger, getLogger
from math import inf, isnan
from typing import TYPE_CHECKING, Any, Final, Generic, Union

from . import lowlevel
from ._guard import ResourceGuard
from ._lock import Lock, RLock
from ._semaphore import BinarySemaphore
from .lowlevel import (
    ThreadOnceLock,
    async_checkpoint,
    create_async_event,
    create_green_event,
    current_async_task_ident,
    current_green_task_ident,
    green_checkpoint,
    green_clock,
    lazydeque,
)
from .meta import DEFAULT, MISSING, DefaultType

if sys.version_info >= (3, 13):
    from typing import TypeVar
else:
    from typing_extensions import TypeVar

if sys.version_info >= (3, 11):
    from typing import overload
else:
    from typing_extensions import overload

if sys.version_info >= (3, 9):
    from collections.abc import Callable, Generator
else:
    from typing import Callable, Generator

if TYPE_CHECKING:
    from types import TracebackType

    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self

try:
    from sys import _is_gil_enabled
except ImportError:
    __GIL_ENABLED: Final[bool] = True
else:
    __GIL_ENABLED: Final[bool] = _is_gil_enabled()

_USE_ONCELOCK_FORCED: Final[bool] = not __GIL_ENABLED

LOGGER: Final[Logger] = getLogger(__name__)

_T = TypeVar("_T")
_T_co = TypeVar(
    "_T_co",
    bound=Union[
        Lock,
        BinarySemaphore,
        lowlevel.ThreadRLock,
        lowlevel.ThreadLock,
        None,
    ],
    default=RLock,
    covariant=True,
)
_S_co = TypeVar(
    "_S_co",
    bound=Callable[[], float],
    default=Callable[[], float],
    covariant=True,
)


class Condition(Generic[_T_co, _S_co]):
    """..."""

    __slots__ = (
        "__weakref__",
        "_impl",
    )

    @overload
    def __new__(
        cls,
        /,
        lock: DefaultType = DEFAULT,
        timer: DefaultType = DEFAULT,
    ) -> Condition[RLock, Callable[[], int]]: ...
    @overload
    def __new__(
        cls,
        /,
        lock: DefaultType = DEFAULT,
        *,
        timer: _S_co,
    ) -> Condition[RLock, _S_co]: ...
    @overload
    def __new__(
        cls,
        /,
        lock: _T_co,
        timer: DefaultType = DEFAULT,
    ) -> Condition[_T_co, Callable[[], int]]: ...
    @overload
    def __new__(cls, /, lock: _T_co, timer: _S_co) -> Self: ...
    def __new__(cls, /, lock=DEFAULT, timer=DEFAULT):
        """..."""

        if lock is DEFAULT:
            lock = RLock()

        if timer is DEFAULT:
            timer = count().__next__

        if lock is None:
            # lockless
            imp = _BaseCondition
        elif isinstance(lock, Lock):
            # aiologic.RLock | aiologic.Lock
            imp = _RMixedCondition
        elif isinstance(lock, BinarySemaphore):
            # aiologic.BoundedBinarySemaphore | aiologic.BinarySemaphore
            imp = _MixedCondition
        elif hasattr(lock, "_is_owned"):
            # aiologic.lowlevel.ThreadRLock
            imp = _RSyncCondition
        else:
            # aiologic.lowlevel.ThreadLock
            imp = _SyncCondition

        if cls is Condition:
            return imp.__new__(imp, lock, timer)

        self = object.__new__(cls)

        self._impl = imp(lock, timer)

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
            >>> orig = Condition()
            >>> copy = Condition(*orig.__getnewargs__())
            >>> copy.lock is orig.lock
            True
        """

        try:
            timer_is_count = self.timer.__self__.__class__ is count
        except AttributeError:
            timer_is_count = False

        if timer_is_count:
            return (self.lock,)

        return (self.lock, self.timer)

    def __getstate__(self, /) -> None:
        """
        Disables the use of internal state for pickling and copying.
        """

        return None

    def __copy__(self, /) -> Self:
        """..."""

        try:
            timer_is_count = self.timer.__self__.__class__ is count
        except AttributeError:
            timer_is_count = False

        if timer_is_count:
            return self.__class__(self.lock)

        return self.__class__(self.lock, self.timer)

    def __repr__(self, /) -> str:
        """..."""

        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        try:
            timer_is_count = self.timer.__self__.__class__ is count
        except AttributeError:
            timer_is_count = False

        if self.lock is None:
            lock_repr = repr(None)
        else:
            lock_cls = self.lock.__class__
            lock_repr = f"<{lock_cls.__module__}.{lock_cls.__qualname__}>"

        if timer_is_count:
            object_repr = f"{cls_repr}({lock_repr})"
        else:
            object_repr = f"{cls_repr}({lock_repr}, timer={self.timer!r})"

        extra = f"waiting={self.waiting}"

        return f"<{object_repr} at {id(self):#x} [{extra}]>"

    def __bool__(self, /) -> bool:
        """
        Returns :data:`True` if the underlying lock is used by any task.

        If there is no lock, returns :data:`False`.

        Used by the standard :ref:`truth testing procedure <truth>`.

        Example:
            >>> accessing = Condition()
            >>> bool(accessing)
            False
            >>> with accessing:  # condition variable is in use
            ...     bool(accessing)
            True
            >>> bool(accessing)
            False
        """

        return bool(self._impl)

    async def __aenter__(self, /) -> Self:
        """..."""

        return await self._impl.__aenter__()

    def __enter__(self, /) -> Self:
        """..."""

        return self._impl.__enter__()

    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """..."""

        return await self._impl.__aexit__(exc_type, exc_value, traceback)

    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """..."""

        return self._impl.__exit__(exc_type, exc_value, traceback)

    def __await__(self, /) -> Generator[Any, Any, bool]:
        """..."""

        return (yield from self._impl.__await__())

    def wait(self, /, timeout: float | None = None) -> bool:
        """..."""

        return self._impl.wait(timeout)

    async def for_(
        self,
        /,
        predicate: Callable[[], _T],
        *,
        delegate: bool = True,
    ) -> _T:
        """..."""

        return await self._impl.for_(predicate, delegate=delegate)

    def wait_for(
        self,
        /,
        predicate: Callable[[], _T],
        timeout: float | None = None,
        *,
        delegate: bool = True,
    ) -> _T:
        """..."""

        return self._impl.wait_for(predicate, timeout, delegate=delegate)

    def notify(
        self,
        /,
        count: int = 1,
        *,
        deadline: float | None = None,
    ) -> int:
        """..."""

        return self._impl.notify(count, deadline=deadline)

    def notify_all(self, /, *, deadline: float | None = None) -> int:
        """..."""

        return self._impl.notify_all(deadline=deadline)

    @property
    def lock(self, /) -> _T_co:
        """
        The underlying lock used by the condition variable.
        """

        return self._impl.lock

    @property
    def timer(self, /) -> _S_co:
        """
        The callable object used by the condition variable.
        """

        return self._impl.timer

    @property
    def waiting(self, /) -> int:
        """
        The current number of tasks waiting to be notified.

        It represents the length of the waiting queue and thus changes
        immediately.
        """

        return self._impl.waiting


class _BaseCondition(Condition[_T_co, _S_co]):
    __slots__ = (
        "_lock",
        "_notifying",
        "_timer",
        "_waiters",
    )

    def __new__(cls, /, lock: _T_co, timer: _S_co) -> Self:
        self = object.__new__(cls)

        self._lock = lock
        self._timer = timer

        self._waiters = lazydeque()

        self._notifying = ResourceGuard(action="notifying")

        return self

    def __reduce__(self, /) -> tuple[Any, ...]:
        try:
            timer_is_count = self._timer.__self__.__class__ is count
        except AttributeError:
            timer_is_count = False

        if timer_is_count:
            return (Condition, (self._lock,))

        return (Condition, (self._lock, self._timer))

    def __copy__(self, /) -> Self:
        try:
            timer_is_count = self.timer.__self__.__class__ is count
        except AttributeError:
            timer_is_count = False

        if timer_is_count:
            return self.__class__(self.lock, count().__next__)

        return self.__class__(self.lock, self.timer)

    def __repr__(self, /) -> str:
        cls = Condition
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        try:
            timer_is_count = self._timer.__self__.__class__ is count
        except AttributeError:
            timer_is_count = False

        if self._lock is None:
            lock_repr = repr(None)
        else:
            lock_cls = self._lock.__class__
            lock_repr = f"<{lock_cls.__module__}.{lock_cls.__qualname__}>"

        if timer_is_count:
            object_repr = f"{cls_repr}({lock_repr})"
        else:
            object_repr = f"{cls_repr}({lock_repr}, timer={self._timer!r})"

        extra = f"waiting={len(self._waiters)}"

        return f"<{object_repr} at {id(self):#x} [{extra}]>"

    def __bool__(self, /) -> bool:
        return False

    async def __aenter__(self, /) -> Self:
        return self

    def __enter__(self, /) -> Self:
        return self

    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    def __await__(self, /) -> Generator[Any, Any, bool]:
        if not self._async_owned():
            msg = "cannot wait on un-acquired lock"
            raise RuntimeError(msg)

        return (yield from self._async_wait(None).__await__())

    def wait(self, /, timeout: float | None = None) -> bool:
        if not self._green_owned():
            msg = "cannot wait on un-acquired lock"
            raise RuntimeError(msg)

        return self._green_wait(None, timeout)

    async def for_(
        self,
        /,
        predicate: Callable[[], _T],
        *,
        delegate: bool = True,
    ) -> _T:
        if not self._async_owned():
            msg = "cannot wait on un-acquired lock"
            raise RuntimeError(msg)

        if result := predicate():
            await async_checkpoint()

            return result

        while True:
            if delegate:
                await self._async_wait(predicate)
            else:
                await self._async_wait(None)

            if result := predicate():
                return result

    def wait_for(
        self,
        /,
        predicate: Callable[[], _T],
        timeout: float | None = None,
        *,
        delegate: bool = True,
    ) -> _T:
        if not self._green_owned():
            msg = "cannot wait on un-acquired lock"
            raise RuntimeError(msg)

        if result := predicate():
            green_checkpoint()

            return result

        deadline = None

        while True:
            if timeout is not None:
                if isinstance(timeout, int):
                    try:
                        timeout = float(timeout)
                    except OverflowError:
                        timeout = (-1 if timeout < 0 else 1) * inf

                if isnan(timeout):
                    msg = "timeout must be non-NaN"
                    raise ValueError(msg)

                if timeout < 0:
                    msg = "timeout must be non-negative"
                    raise ValueError(msg)

                if deadline is None:
                    deadline = green_clock() + timeout
                else:
                    timeout = deadline - green_clock()

                    if timeout < 0:
                        return result

            if delegate:
                self._green_wait(predicate, timeout)
            else:
                self._green_wait(None, timeout)

            if result := predicate():
                return result

    def notify(
        self,
        /,
        count: int = 1,
        *,
        deadline: float | None = None,
    ) -> int:
        waiters = self._waiters

        notified = 0

        while waiters and notified != count:
            try:
                token = waiters[0]
            except IndexError:
                break
            else:
                event, predicate, time, *_ = token

                if deadline is None:
                    deadline = self._timer()

                if time > deadline:
                    break

                remove = True
                rotate = False

                if predicate is not None:
                    if not self:
                        msg = "cannot notify for predicate on un-acquired lock"
                        raise RuntimeError(msg)

                    with self._notifying:
                        try:
                            result = predicate()
                        except Exception as exc:
                            token[4] = exc

                            if remove := event.set():
                                notified += 1
                            else:
                                LOGGER.exception(
                                    "exception calling predicate for %r",
                                    self,
                                )
                        else:
                            if result:
                                token[3] = result
                            else:
                                token[2] = self._timer()

                                rotate = True

                if not rotate:
                    if remove := event.set():
                        notified += 1

                try:
                    if remove or waiters[0] is token:
                        if _USE_ONCELOCK_FORCED:
                            ThreadOnceLock.acquire(event)
                            try:
                                if waiters[0] is token:
                                    waiters.remove(token)
                            finally:
                                ThreadOnceLock.release(event)
                        else:
                            waiters.remove(token)
                except ValueError:  # waiters does not contain token
                    continue
                except IndexError:  # waiters is empty
                    break
                else:
                    if not rotate:
                        continue

                    waiters.append(token)

                    if event.is_set() or event.cancelled():
                        try:
                            if waiters[0] is token:
                                if _USE_ONCELOCK_FORCED:
                                    ThreadOnceLock.acquire(event)
                                    try:
                                        if waiters[0] is token:
                                            waiters.remove(token)
                                    finally:
                                        ThreadOnceLock.release(event)
                                else:
                                    waiters.remove(token)
                        except ValueError:  # waiters does not contain token
                            continue
                        except IndexError:  # waiters is empty
                            break

        return notified

    def notify_all(self, /, *, deadline: float | None = None) -> int:
        return self.notify(-1, deadline=deadline)

    @overload
    async def _async_wait(self, /, predicate: Callable[[], _T]) -> _T: ...
    @overload
    async def _async_wait(self, /, predicate: None) -> bool: ...
    async def _async_wait(self, /, predicate):
        if predicate is not None:
            self._waiters.append(
                token := [
                    event := create_async_event(locking=_USE_ONCELOCK_FORCED),
                    predicate,
                    self._timer(),
                    MISSING,  # predicate result
                    MISSING,  # predicate exception
                ]
            )
        else:
            self._waiters.append(
                token := (
                    event := create_async_event(locking=_USE_ONCELOCK_FORCED),
                    None,
                    self._timer(),
                )
            )

        success = False

        try:
            success = await event
        except BaseException:
            if predicate is not None:
                if token[4] is not MISSING:
                    LOGGER.error(
                        "exception calling predicate for %r",
                        self,
                        exc_info=token[4],
                    )

            raise
        finally:
            if not success:
                if event.cancelled():
                    try:
                        self._waiters.remove(token)
                    except ValueError:
                        pass
                else:
                    self.notify()

        if predicate is not None:
            if token[3] is not MISSING:
                return token[3]

            if token[4] is not MISSING:
                try:
                    raise token[4]
                finally:
                    token[4] = MISSING

            return predicate()

        return success

    @overload
    def _green_wait(
        self,
        /,
        predicate: Callable[[], _T],
        timeout: float | None,
    ) -> _T: ...
    @overload
    def _green_wait(
        self,
        /,
        predicate: None,
        timeout: float | None,
    ) -> bool: ...
    def _green_wait(self, /, predicate, timeout):
        if predicate is not None:
            self._waiters.append(
                token := [
                    event := create_green_event(locking=_USE_ONCELOCK_FORCED),
                    predicate,
                    self._timer(),
                    MISSING,  # predicate result
                    MISSING,  # predicate exception
                ]
            )
        else:
            self._waiters.append(
                token := (
                    event := create_green_event(locking=_USE_ONCELOCK_FORCED),
                    None,
                    self._timer(),
                )
            )

        success = False

        try:
            success = event.wait(timeout)
        except BaseException:
            if predicate is not None:
                if token[4] is not MISSING:
                    LOGGER.error(
                        "exception calling predicate for %r",
                        self,
                        exc_info=token[4],
                    )

            raise
        finally:
            if not success:
                if event.cancelled():
                    try:
                        self._waiters.remove(token)
                    except ValueError:
                        pass
                else:
                    self.notify()

        if predicate is not None:
            if token[3] is not MISSING:
                return token[3]

            if token[4] is not MISSING:
                try:
                    raise token[4]
                finally:
                    token[4] = MISSING

            return predicate()

        return success

    def _async_owned(self, /) -> bool:
        return True

    def _green_owned(self, /) -> bool:
        return True

    @property
    def lock(self, /) -> _T_co:
        return self._lock

    @property
    def timer(self, /) -> _S_co:
        return self._timer

    @property
    def waiting(self, /) -> int:
        return len(self._waiters)


class _SyncCondition(_BaseCondition[_T_co, _S_co]):
    __slots__ = ("_counts",)

    def __new__(cls, /, lock: _T_co, timer: _S_co) -> Self:
        self = object.__new__(cls)

        self._counts = defaultdict(int)

        self._lock = lock
        self._timer = timer

        self._waiters = lazydeque()

        self._notifying = ResourceGuard(action="notifying")

        return self

    def __bool__(self, /) -> bool:
        return self._lock.locked()

    async def __aenter__(self, /) -> Self:
        if self._lock.acquire():
            self._counts[current_async_task_ident()] += 1

        return self

    def __enter__(self, /) -> Self:
        if self._lock.acquire():
            self._counts[current_green_task_ident()] += 1

        return self

    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._counts:
            task = current_async_task_ident()

            count = self._counts.pop(task, 0)
        else:
            count = 0

        if count < 1:
            return

        if count > 1:
            self._counts[task] = count - 1

        self._lock.release()

    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._counts:
            task = current_green_task_ident()

            count = self._counts.pop(task, 0)
        else:
            count = 0

        if count < 1:
            return

        if count > 1:
            self._counts[task] = count - 1

        self._lock.release()

    @overload
    async def _async_wait(self, /, predicate: Callable[[], _T]) -> _T: ...
    @overload
    async def _async_wait(self, /, predicate: None) -> bool: ...
    async def _async_wait(self, /, predicate):
        if predicate is not None:
            self._waiters.append(
                token := [
                    event := create_async_event(locking=_USE_ONCELOCK_FORCED),
                    predicate,
                    self._timer(),
                    MISSING,  # predicate result
                    MISSING,  # predicate exception
                ]
            )
        else:
            self._waiters.append(
                token := (
                    event := create_async_event(locking=_USE_ONCELOCK_FORCED),
                    None,
                    self._timer(),
                )
            )

        success = False

        try:
            if self._counts:
                task = current_async_task_ident()

                count = self._counts.pop(task, 0)
            else:
                count = 0

            self._lock.release()

            try:
                success = await event
            finally:
                self._lock.acquire()

                if count:
                    self._counts[task] = count
        except BaseException:
            if predicate is not None:
                if token[4] is not MISSING:
                    LOGGER.error(
                        "exception calling predicate for %r",
                        self,
                        exc_info=token[4],
                    )

            raise
        finally:
            if not success:
                if event.cancelled():
                    try:
                        self._waiters.remove(token)
                    except ValueError:
                        pass
                else:
                    self.notify()

        if predicate is not None:
            if token[3] is not MISSING:
                return token[3]

            if token[4] is not MISSING:
                try:
                    raise token[4]
                finally:
                    token[4] = MISSING

            return predicate()

        return success

    @overload
    def _green_wait(
        self,
        /,
        predicate: Callable[[], _T],
        timeout: float | None,
    ) -> _T: ...
    @overload
    def _green_wait(
        self,
        /,
        predicate: None,
        timeout: float | None,
    ) -> bool: ...
    def _green_wait(self, /, predicate, timeout):
        if predicate is not None:
            self._waiters.append(
                token := [
                    event := create_green_event(locking=_USE_ONCELOCK_FORCED),
                    predicate,
                    self._timer(),
                    MISSING,  # predicate result
                    MISSING,  # predicate exception
                ]
            )
        else:
            self._waiters.append(
                token := (
                    event := create_green_event(locking=_USE_ONCELOCK_FORCED),
                    None,
                    self._timer(),
                )
            )

        success = False

        try:
            if self._counts:
                task = current_green_task_ident()

                count = self._counts.pop(task, 0)
            else:
                count = 0

            self._lock.release()

            try:
                success = event.wait(timeout)
            finally:
                self._lock.acquire()

                if count:
                    self._counts[task] = count
        except BaseException:
            if predicate is not None:
                if token[4] is not MISSING:
                    LOGGER.error(
                        "exception calling predicate for %r",
                        self,
                        exc_info=token[4],
                    )

            raise
        finally:
            if not success:
                if event.cancelled():
                    try:
                        self._waiters.remove(token)
                    except ValueError:
                        pass
                else:
                    self.notify()

        if predicate is not None:
            if token[3] is not MISSING:
                return token[3]

            if token[4] is not MISSING:
                try:
                    raise token[4]
                finally:
                    token[4] = MISSING

            return predicate()

        return success

    def _async_owned(self, /) -> bool:
        return self._lock.locked()

    def _green_owned(self, /) -> bool:
        return self._lock.locked()


class _RSyncCondition(_BaseCondition[_T_co, _S_co]):
    __slots__ = ()

    if sys.version_info >= (3, 14):

        def __bool__(self, /) -> bool:
            return self._lock.locked()

    else:

        def __bool__(self, /) -> bool:
            if self._lock._is_owned():
                return True

            if self._lock.acquire(False):
                self._lock.release()

                return False

            return True

    async def __aenter__(self, /) -> Self:
        self._lock.acquire()

        return self

    def __enter__(self, /) -> Self:
        self._lock.acquire()

        return self

    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._lock._is_owned():
            self._lock.release()

    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._lock._is_owned():
            self._lock.release()

    @overload
    async def _async_wait(self, /, predicate: Callable[[], _T]) -> _T: ...
    @overload
    async def _async_wait(self, /, predicate: None) -> bool: ...
    async def _async_wait(self, /, predicate):
        if predicate is not None:
            self._waiters.append(
                token := [
                    event := create_async_event(locking=_USE_ONCELOCK_FORCED),
                    predicate,
                    self._timer(),
                    MISSING,  # predicate result
                    MISSING,  # predicate exception
                ]
            )
        else:
            self._waiters.append(
                token := (
                    event := create_async_event(locking=_USE_ONCELOCK_FORCED),
                    None,
                    self._timer(),
                )
            )

        success = False

        try:
            state = self._lock._release_save()

            try:
                success = await event
            finally:
                self._lock._acquire_restore(state)
        except BaseException:
            if predicate is not None:
                if token[4] is not MISSING:
                    LOGGER.error(
                        "exception calling predicate for %r",
                        self,
                        exc_info=token[4],
                    )

            raise
        finally:
            if not success:
                if event.cancelled():
                    try:
                        self._waiters.remove(token)
                    except ValueError:
                        pass
                else:
                    self.notify()

        if predicate is not None:
            if token[3] is not MISSING:
                return token[3]

            if token[4] is not MISSING:
                try:
                    raise token[4]
                finally:
                    token[4] = MISSING

            return predicate()

        return success

    @overload
    def _green_wait(
        self,
        /,
        predicate: Callable[[], _T],
        timeout: float | None,
    ) -> _T: ...
    @overload
    def _green_wait(
        self,
        /,
        predicate: None,
        timeout: float | None,
    ) -> bool: ...
    def _green_wait(self, /, predicate, timeout):
        if predicate is not None:
            self._waiters.append(
                token := [
                    event := create_green_event(locking=_USE_ONCELOCK_FORCED),
                    predicate,
                    self._timer(),
                    MISSING,  # predicate result
                    MISSING,  # predicate exception
                ]
            )
        else:
            self._waiters.append(
                token := (
                    event := create_green_event(locking=_USE_ONCELOCK_FORCED),
                    None,
                    self._timer(),
                )
            )

        success = False

        try:
            state = self._lock._release_save()

            try:
                success = event.wait(timeout)
            finally:
                self._lock._acquire_restore(state)
        except BaseException:
            if predicate is not None:
                if token[4] is not MISSING:
                    LOGGER.error(
                        "exception calling predicate for %r",
                        self,
                        exc_info=token[4],
                    )

            raise
        finally:
            if not success:
                if event.cancelled():
                    try:
                        self._waiters.remove(token)
                    except ValueError:
                        pass
                else:
                    self.notify()

        if predicate is not None:
            if token[3] is not MISSING:
                return token[3]

            if token[4] is not MISSING:
                try:
                    raise token[4]
                finally:
                    token[4] = MISSING

            return predicate()

        return success

    def _async_owned(self, /) -> bool:
        return self._lock._is_owned()

    def _green_owned(self, /) -> bool:
        return self._lock._is_owned()


class _MixedCondition(_BaseCondition[_T_co, _S_co]):
    __slots__ = ("_counts",)

    def __new__(cls, /, lock: _T_co, timer: _S_co) -> Self:
        self = object.__new__(cls)

        self._counts = defaultdict(int)

        self._lock = lock
        self._timer = timer

        self._waiters = lazydeque()

        self._notifying = ResourceGuard(action="notifying")

        return self

    def __bool__(self, /) -> bool:
        return not self._lock.value

    async def __aenter__(self, /) -> Self:
        if await self._lock.async_acquire():
            self._counts[current_async_task_ident()] += 1

        return self

    def __enter__(self, /) -> Self:
        if self._lock.green_acquire():
            self._counts[current_green_task_ident()] += 1

        return self

    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._counts:
            task = current_async_task_ident()

            count = self._counts.pop(task, 0)
        else:
            count = 0

        if count < 1:
            return

        if count > 1:
            self._counts[task] = count - 1

        self._lock.async_release()

    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._counts:
            task = current_green_task_ident()

            count = self._counts.pop(task, 0)
        else:
            count = 0

        if count < 1:
            return

        if count > 1:
            self._counts[task] = count - 1

        self._lock.green_release()

    async def for_(
        self,
        /,
        predicate: Callable[[], _T],
        *,
        delegate: bool = True,
    ) -> _T:
        if not self._async_owned():
            msg = "cannot wait on un-acquired lock"
            raise RuntimeError(msg)

        if result := predicate():
            await async_checkpoint()

            return result

        if not delegate:
            while True:
                await self._async_wait(None)

                if result := predicate():
                    return result

        return await self._async_wait(predicate)

    def wait_for(
        self,
        /,
        predicate: Callable[[], _T],
        timeout: float | None = None,
        *,
        delegate: bool = True,
    ) -> _T:
        if not self._green_owned():
            msg = "cannot wait on un-acquired lock"
            raise RuntimeError(msg)

        if result := predicate():
            green_checkpoint()

            return result

        if not delegate:
            deadline = None

            while True:
                if timeout is not None:
                    if isinstance(timeout, int):
                        try:
                            timeout = float(timeout)
                        except OverflowError:
                            timeout = (-1 if timeout < 0 else 1) * inf

                    if isnan(timeout):
                        msg = "timeout must be non-NaN"
                        raise ValueError(msg)

                    if timeout < 0:
                        msg = "timeout must be non-negative"
                        raise ValueError(msg)

                    if deadline is None:
                        deadline = green_clock() + timeout
                    else:
                        timeout = deadline - green_clock()

                        if timeout < 0:
                            return result

                self._green_wait(None, timeout)

                if result := predicate():
                    return result

        return self._green_wait(predicate, timeout)

    def notify(
        self,
        /,
        count: int = 1,
        *,
        deadline: float | None = None,
    ) -> int:
        if not self:
            msg = "cannot notify on un-acquired lock"
            raise RuntimeError(msg)

        with self._notifying:
            waiters = self._waiters

            notified = 0

            while waiters and notified != count:
                try:
                    token = waiters[0]
                except IndexError:
                    break
                else:
                    event, predicate, time, *_ = token

                    if deadline is None:
                        deadline = self._timer()

                    if time > deadline:
                        break

                    remove = True
                    rotate = False

                    if predicate is not None:
                        try:
                            result = predicate()
                        except Exception as exc:
                            token[4] = exc

                            if remove := self._lock._park(token):
                                notified += 1
                            else:
                                LOGGER.exception(
                                    "exception calling predicate for %r",
                                    self,
                                )
                        else:
                            if result:
                                token[3] = result
                            else:
                                token[2] = self._timer()

                                rotate = True

                    if not rotate:
                        if remove := self._lock._park(token):
                            notified += 1

                    try:
                        if remove or waiters[0] is token:
                            if _USE_ONCELOCK_FORCED:
                                ThreadOnceLock.acquire(event)
                                try:
                                    if waiters[0] is token:
                                        waiters.remove(token)
                                finally:
                                    ThreadOnceLock.release(event)
                            else:
                                waiters.remove(token)
                    except ValueError:  # token not in waiters
                        continue
                    except IndexError:  # waiters is empty
                        break
                    else:
                        if not rotate:
                            continue

                        waiters.append(token)

                        if event.is_set() or event.cancelled():
                            try:
                                if waiters[0] is token:
                                    if _USE_ONCELOCK_FORCED:
                                        ThreadOnceLock.acquire(event)
                                        try:
                                            if waiters[0] is token:
                                                waiters.remove(token)
                                        finally:
                                            ThreadOnceLock.release(event)
                                    else:
                                        waiters.remove(token)
                            except ValueError:  # token not in waiters
                                continue
                            except IndexError:  # waiters is empty
                                break

            return notified

    @overload
    async def _async_wait(self, /, predicate: Callable[[], _T]) -> _T: ...
    @overload
    async def _async_wait(self, /, predicate: None) -> bool: ...
    async def _async_wait(self, /, predicate):
        self._waiters.append(
            token := [
                event := create_async_event(locking=_USE_ONCELOCK_FORCED),
                predicate,
                self._timer(),
                MISSING,  # predicate result
                MISSING,  # predicate exception
                False,  # reparked
            ]
        )

        success = False

        try:
            if self._counts:
                task = current_async_task_ident()

                count = self._counts.pop(task, 0)
            else:
                count = 0

            self._lock.async_release()

            try:
                success = await event
            finally:
                if event.cancelled():
                    if token[5]:
                        self._lock._unpark(event)

                    await self._lock._async_acquire(_shield=True)

                self._lock._after_park()

                if count:
                    self._counts[task] = count
        except BaseException:
            if token[4] is not MISSING:
                LOGGER.error(
                    "exception calling predicate for %r",
                    self,
                    exc_info=token[4],
                )

            raise
        finally:
            if not success:
                if event.cancelled() and not token[5]:
                    try:
                        self._waiters.remove(token)
                    except ValueError:
                        pass
                else:
                    self.notify()

        if predicate is not None:
            if token[3] is not MISSING:
                return token[3]

            if token[4] is not MISSING:
                try:
                    raise token[4]
                finally:
                    token[4] = MISSING

            return predicate()

        return success

    @overload
    def _green_wait(
        self,
        /,
        predicate: Callable[[], _T],
        timeout: float | None,
    ) -> _T: ...
    @overload
    def _green_wait(
        self,
        /,
        predicate: None,
        timeout: float | None,
    ) -> bool: ...
    def _green_wait(self, /, predicate, timeout):
        self._waiters.append(
            token := [
                event := create_green_event(locking=_USE_ONCELOCK_FORCED),
                predicate,
                self._timer(),
                MISSING,  # predicate result
                MISSING,  # predicate exception
                False,  # reparked
            ]
        )

        success = False

        try:
            if self._counts:
                task = current_green_task_ident()

                count = self._counts.pop(task, 0)
            else:
                count = 0

            self._lock.green_release()

            try:
                success = event.wait(timeout)
            finally:
                if event.cancelled():
                    if token[5]:
                        self._lock._unpark(event)

                    self._lock._green_acquire(_shield=True)

                self._lock._after_park()

                if count:
                    self._counts[task] = count
        except BaseException:
            if token[4] is not MISSING:
                LOGGER.error(
                    "exception calling predicate for %r",
                    self,
                    exc_info=token[4],
                )

            raise
        finally:
            if not success:
                if event.cancelled() and not token[5]:
                    try:
                        self._waiters.remove(token)
                    except ValueError:
                        pass
                else:
                    self.notify()

        if predicate is not None:
            if token[3] is not MISSING:
                return token[3]

            if token[4] is not MISSING:
                try:
                    raise token[4]
                finally:
                    token[4] = MISSING

            return predicate()

        return success

    def _async_owned(self, /) -> bool:
        return not self._lock.value

    def _green_owned(self, /) -> bool:
        return not self._lock.value


class _RMixedCondition(_BaseCondition[_T_co, _S_co]):
    __slots__ = ()

    def __bool__(self, /) -> bool:
        return self._lock.locked()

    async def __aenter__(self, /) -> Self:
        await self._lock.async_acquire()

        return self

    def __enter__(self, /) -> Self:
        self._lock.green_acquire()

        return self

    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._lock.async_owned():
            self._lock.async_release()

    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._lock.green_owned():
            self._lock.green_release()

    notify = _MixedCondition.notify

    @overload
    async def _async_wait(self, /, predicate: Callable[[], _T]) -> _T: ...
    @overload
    async def _async_wait(self, /, predicate: None) -> bool: ...
    async def _async_wait(self, /, predicate):
        self._waiters.append(
            token := [
                event := create_async_event(locking=_USE_ONCELOCK_FORCED),
                predicate,
                self._timer(),
                MISSING,  # predicate result
                MISSING,  # predicate exception
                False,  # reparked
                state := (self._lock.owner, getattr(self._lock, "count", 1)),
            ]
        )

        success = False

        try:
            if (count := state[1]) > 1:
                self._lock.async_release(count)
            else:
                self._lock.async_release()

            try:
                success = await event
            finally:
                if event.cancelled():
                    if token[5]:
                        self._lock._unpark(event, state)

                    await self._lock._async_acquire_on_behalf_of(
                        *state,
                        _shield=True,
                    )
                else:
                    self._lock._after_park()
        except BaseException:
            if token[4] is not MISSING:
                LOGGER.error(
                    "exception calling predicate for %r",
                    self,
                    exc_info=token[4],
                )

            raise
        finally:
            if not success:
                if event.cancelled() and not token[5]:
                    try:
                        self._waiters.remove(token)
                    except ValueError:
                        pass
                else:
                    self.notify()

        if predicate is not None:
            if token[3] is not MISSING:
                return token[3]

            if token[4] is not MISSING:
                try:
                    raise token[4]
                finally:
                    token[4] = MISSING

            return predicate()

        return success

    @overload
    def _green_wait(
        self,
        /,
        predicate: Callable[[], _T],
        timeout: float | None,
    ) -> _T: ...
    @overload
    def _green_wait(
        self,
        /,
        predicate: None,
        timeout: float | None,
    ) -> bool: ...
    def _green_wait(self, /, predicate, timeout):
        self._waiters.append(
            token := [
                event := create_green_event(locking=_USE_ONCELOCK_FORCED),
                predicate,
                self._timer(),
                MISSING,  # predicate result
                MISSING,  # predicate exception
                False,  # reparked
                state := (self._lock.owner, getattr(self._lock, "count", 1)),
            ]
        )

        success = False

        try:
            if (count := state[1]) > 1:
                self._lock.green_release(count)
            else:
                self._lock.green_release()

            try:
                success = event.wait(timeout)
            finally:
                if event.cancelled():
                    if token[5]:
                        self._lock._unpark(event, state)

                    self._lock._green_acquire_on_behalf_of(
                        *state,
                        _shield=True,
                    )
                else:
                    self._lock._after_park()
        except BaseException:
            if token[4] is not MISSING:
                LOGGER.error(
                    "exception calling predicate for %r",
                    self,
                    exc_info=token[4],
                )

            raise
        finally:
            if not success:
                if event.cancelled() and not token[5]:
                    try:
                        self._waiters.remove(token)
                    except ValueError:
                        pass
                else:
                    self.notify()

        if predicate is not None:
            if token[3] is not MISSING:
                return token[3]

            if token[4] is not MISSING:
                try:
                    raise token[4]
                finally:
                    token[4] = MISSING

            return predicate()

        return success

    def _async_owned(self, /) -> bool:
        return self._lock.async_owned()

    def _green_owned(self, /) -> bool:
        return self._lock.green_owned()
