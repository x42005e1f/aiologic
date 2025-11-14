#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import os
import sys

from itertools import count
from typing import TYPE_CHECKING, Any, Final

from ._flag import Flag
from .lowlevel import (
    ThreadOnceLock,
    async_checkpoint,
    create_async_event,
    create_green_event,
    green_checkpoint,
    lazydeque,
)
from .meta import DEFAULT, MISSING, DefaultType, MissingType, copies

if sys.version_info >= (3, 11):
    from typing import overload
else:
    from typing_extensions import overload

if TYPE_CHECKING:
    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self

    if sys.version_info >= (3, 9):
        from collections.abc import Callable, Generator
    else:
        from typing import Callable, Generator

try:
    from sys import _is_gil_enabled
except ImportError:
    __GIL_ENABLED: Final[bool] = True
else:
    __GIL_ENABLED: Final[bool] = _is_gil_enabled()

_PERFECT_FAIRNESS_ENABLED: Final[bool] = bool(
    os.getenv(
        "AIOLOGIC_PERFECT_FAIRNESS",
        "1" if __GIL_ENABLED else "",
    )
)

_USE_ONCELOCK: Final[bool] = _PERFECT_FAIRNESS_ENABLED and not __GIL_ENABLED
_USE_ONCELOCK_FORCED: Final[bool] = not __GIL_ENABLED


class Event:
    """..."""

    __slots__ = (
        "__weakref__",
        "_is_unset",
        "_waiters",
    )

    def __new__(cls, /) -> Self:
        """..."""

        self = object.__new__(cls)

        self._is_unset = True
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
            >>> orig = Event()
            >>> copy = Event(*orig.__getnewargs__())
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

        if not self._is_unset:
            extra = "set"
        else:
            extra = f"unset, waiting={len(self._waiters)}"

        return f"<{object_repr} at {id(self):#x} [{extra}]>"

    def __bool__(self, /) -> bool:
        """
        Returns :data:`True` if the event is set.

        Used by the standard :ref:`truth testing procedure <truth>`.

        Example:
            >>> finished = Event()  # event is unset
            >>> bool(finished)
            False
            >>> finished.set()  # event is set
            >>> bool(finished)
            True
        """

        return not self._is_unset

    def __await__(self, /) -> Generator[Any, Any, bool]:
        """..."""

        if not self._is_unset:
            yield from async_checkpoint().__await__()

            self._wakeup()

            return True

        self._waiters.append(
            event := create_async_event(locking=_USE_ONCELOCK)
        )

        if not self._is_unset:
            if event.set():
                try:
                    self._waiters.remove(event)
                except ValueError:
                    pass

        success = False

        try:
            success = yield from event.__await__()
        finally:
            if not success:
                if event.cancelled():
                    try:
                        self._waiters.remove(event)
                    except ValueError:
                        pass

        if success:
            self._wakeup()

        return success

    def wait(self, /, timeout: float | None = None) -> bool:
        """..."""

        if not self._is_unset:
            green_checkpoint()

            self._wakeup()

            return True

        self._waiters.append(
            event := create_green_event(locking=_USE_ONCELOCK)
        )

        if not self._is_unset:
            if event.set():
                try:
                    self._waiters.remove(event)
                except ValueError:
                    pass

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

        if success:
            self._wakeup()

        return success

    def set(self, /) -> None:
        """..."""

        self._is_unset = False
        self._wakeup()

    def is_set(self, /) -> bool:
        """
        Return :data:`True` if the event is set.

        Example:
            >>> event = Event()
            >>> event.is_set()
            False
            >>> event.set()
            >>> event.is_set()
            True
        """

        return not self._is_unset

    def _wakeup(self, /) -> None:
        waiters = self._waiters

        while waiters:
            try:
                if _PERFECT_FAIRNESS_ENABLED:
                    event = waiters[0]
                else:
                    event = waiters.popleft()
            except IndexError:
                break
            else:
                remove = event.set()

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

    @property
    def waiting(self, /) -> int:
        """
        The current number of tasks waiting for the event.

        It represents the length of the waiting queue and thus changes
        immediately.
        """

        return len(self._waiters)


class REvent(Event):
    """..."""

    __slots__ = ("_timer",)

    def __new__(cls, /) -> Self:
        """..."""

        self = object.__new__(cls)

        self._is_unset = Flag()
        self._is_unset.set()

        self._timer = count().__next__
        self._waiters = lazydeque()

        return self

    @copies(Event.__getnewargs__)
    def __getnewargs__(self, /) -> tuple[Any, ...]:
        """
        Returns arguments that can be used to create new instances with the
        same initial values.

        Used by:

        * The :mod:`pickle` module for pickling.
        * The :mod:`copy` module for copying.

        The current state does not affect the arguments.

        Example:
            >>> orig = REvent()
            >>> copy = REvent(*orig.__getnewargs__())
        """

        return Event.__getnewargs__(self)

    @copies(Event.__getstate__)
    def __getstate__(self, /) -> None:
        """
        Disables the use of internal state for pickling and copying.
        """

        return Event.__getstate__(self)

    @copies(Event.__copy__)
    def __copy__(self, /) -> Self:
        """..."""

        return Event.__copy__(self)

    @copies(Event.__repr__)
    def __repr__(self, /) -> str:
        """..."""

        return Event.__repr__(self)

    @copies(Event.__bool__)
    def __bool__(self, /) -> bool:
        """
        Returns :data:`True` if the event is set.

        Used by the standard :ref:`truth testing procedure <truth>`.

        Example:
            >>> running = REvent()  # event is unset
            >>> bool(running)
            False
            >>> running.set()  # event is set
            >>> bool(running)
            True
            >>> running.clear()  # event is unset
            >>> bool(running)
            False
        """

        return Event.__bool__(self)

    def __await__(self, /) -> Generator[Any, Any, bool]:
        """..."""

        if not self._is_unset:
            yield from async_checkpoint().__await__()

            self._wakeup()

            return True

        self._waiters.append(
            token := [
                event := create_async_event(locking=_USE_ONCELOCK_FORCED),
                marker := self._is_unset.get(default_factory=object),
                self._timer(),
                None,
            ]
        )

        if self._is_unset.get(None) is not marker:
            if event.set():
                try:
                    self._waiters.remove(token)
                except ValueError:
                    pass

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

        if success:
            self._wakeup(token[3])

        return success

    def wait(self, /, timeout: float | None = None) -> bool:
        """..."""

        if not self._is_unset:
            green_checkpoint()

            self._wakeup()

            return True

        self._waiters.append(
            token := [
                event := create_green_event(locking=_USE_ONCELOCK_FORCED),
                marker := self._is_unset.get(default_factory=object),
                self._timer(),
                None,
            ]
        )

        if self._is_unset.get(None) is not marker:
            if event.set():
                try:
                    self._waiters.remove(token)
                except ValueError:
                    pass

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

        if success:
            self._wakeup(token[3])

        return success

    def clear(self, /) -> None:
        """..."""

        self._is_unset.set()

    def set(self, /) -> None:
        """..."""

        self._is_unset.clear()
        self._wakeup()

    @copies(Event.is_set)
    def is_set(self, /) -> bool:
        """
        Return :data:`True` if the event is set.

        Example:
            >>> event = REvent()
            >>> event.is_set()
            False
            >>> event.set()
            >>> event.is_set()
            True
            >>> event.clear()
            >>> event.is_set()
            False
        """

        return Event.is_set(self)

    def _wakeup(self, /, deadline: float | None = None) -> None:
        waiters = self._waiters

        while waiters:
            try:
                token = waiters[0]
            except IndexError:
                break
            else:
                event, marker, time, _ = token

                if deadline is None:
                    deadline = self._timer()

                if time > deadline:
                    break

                if self._is_unset.get(None) is marker:
                    break

                token[3] = deadline

                remove = event.set()

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

    @property
    @copies(Event.waiting.fget)
    def waiting(self, /) -> int:
        """
        The current number of tasks waiting for the event.

        It represents the length of the waiting queue and thus changes
        immediately.
        """

        return Event.waiting.fget(self)


class CountdownEvent:
    """..."""

    __slots__ = (
        "__weakref__",
        "_initial_value",
        "_is_unset",
        "_timer",
        "_waiters",
    )

    def __new__(cls, /, initial_value: int | DefaultType = DEFAULT) -> Self:
        """..."""

        if initial_value is DEFAULT:
            initial_value = 0
        elif initial_value < 0:
            msg = "initial_value must be >= 0"
            raise ValueError(msg)

        self = object.__new__(cls)

        self._initial_value = initial_value

        self._is_unset = [object()] * initial_value
        self._timer = count().__next__
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
            >>> orig = CountdownEvent(1)
            >>> orig.initial_value
            1
            >>> copy = CountdownEvent(*orig.__getnewargs__())
            >>> copy.initial_value
            1
        """

        initial_value = self._initial_value

        if initial_value != 0:
            return (initial_value,)

        return ()

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

        initial_value = self._initial_value

        if initial_value == 0:
            object_repr = f"{cls_repr}()"
        else:
            object_repr = f"{cls_repr}({initial_value!r})"

        value = len(self._is_unset)

        if value == 0:
            extra = f"value={value}"
        else:
            extra = f"value={value}, waiting={len(self._waiters)}"

        return f"<{object_repr} at {id(self):#x} [{extra}]>"

    def __bool__(self, /) -> bool:
        """
        Returns :data:`True` if the event is set.

        Used by the standard :ref:`truth testing procedure <truth>`.

        Example:
            >>> done = CountdownEvent()  # event is set
            >>> bool(done)
            True
            >>> done.up()  # event is unset
            >>> bool(done)
            False
            >>> done.down()  # event is set
            >>> bool(done)
            True
        """

        return not self._is_unset

    def __await__(self, /) -> Generator[Any, Any, bool]:
        """..."""

        if not self._is_unset:
            yield from async_checkpoint().__await__()

            self._wakeup()

            return True

        self._waiters.append(
            token := [
                event := create_async_event(locking=_USE_ONCELOCK_FORCED),
                marker := self._get(default_factory=object),
                self._timer(),
                None,
            ]
        )

        if self._get(None) is not marker:
            if event.set():
                try:
                    self._waiters.remove(token)
                except ValueError:
                    pass

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

        if success:
            self._wakeup(token[3])

        return success

    def wait(self, /, timeout: float | None = None) -> bool:
        """..."""

        if not self._is_unset:
            green_checkpoint()

            self._wakeup()

            return True

        self._waiters.append(
            token := [
                event := create_green_event(locking=_USE_ONCELOCK_FORCED),
                marker := self._get(default_factory=object),
                self._timer(),
                None,
            ]
        )

        if self._get(None) is not marker:
            if event.set():
                try:
                    self._waiters.remove(token)
                except ValueError:
                    pass

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

        if success:
            self._wakeup(token[3])

        return success

    def up(self, /, count: int = 1) -> None:
        """..."""

        if count == 1:
            self._is_unset.append(object())
        else:
            self._is_unset.extend([object()] * count)

    def down(self, /) -> None:
        """..."""

        try:
            self._is_unset.pop()
        except IndexError:
            msg = "down() called too many times"
            raise RuntimeError(msg) from None

        self._wakeup()

    def clear(self, /) -> None:
        """..."""

        self._is_unset.clear()
        self._wakeup()

    @overload
    def _get(
        self,
        /,
        default: object = MISSING,
        *,
        default_factory: MissingType = MISSING,
    ) -> object: ...
    @overload
    def _get(
        self,
        /,
        default: MissingType = MISSING,
        *,
        default_factory: Callable[[], object],
    ) -> object: ...
    def _get(self, /, default=MISSING, *, default_factory=MISSING):
        if self._is_unset:
            try:
                return self._is_unset[0]
            except IndexError:
                pass

        if default is not MISSING:
            return default

        if default_factory is not MISSING:
            return default_factory()

        raise LookupError(self)

    def _wakeup(self, /, deadline: float | None = None) -> None:
        waiters = self._waiters

        while waiters:
            try:
                token = waiters[0]
            except IndexError:
                break
            else:
                event, marker, time, _ = token

                if deadline is None:
                    deadline = self._timer()

                if time > deadline:
                    break

                if self._get(None) is marker:
                    break

                token[3] = deadline

                remove = event.set()

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

    @property
    def initial_value(self, /) -> int:
        """
        The initial number of :meth:`down` calls required to set the event.
        """

        return self._initial_value

    @property
    def value(self, /) -> int:
        """
        The current number of :meth:`down` calls remaining to set the event.
        """

        return len(self._is_unset)

    @property
    def waiting(self, /) -> int:
        """
        The current number of tasks waiting for the event.

        It represents the length of the waiting queue and thus changes
        immediately.
        """

        return len(self._waiters)
