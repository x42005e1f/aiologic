#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import os

from collections import deque
from itertools import count
from typing import TYPE_CHECKING, Any, Final, overload

from ._flag import Flag
from .lowlevel import (
    MISSING,
    MissingType,
    async_checkpoint,
    create_async_event,
    create_green_event,
    green_checkpoint,
)
from .lowlevel._utils import _copies as copies

if TYPE_CHECKING:
    import sys

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


class Event:
    """..."""

    __slots__ = (
        "__weakref__",
        "_is_unset",
        "_waiters",
    )

    def __new__(cls, /, is_set: bool = False) -> Self:
        """..."""

        self = object.__new__(cls)

        self._is_unset = not is_set
        self._waiters = deque()

        return self

    def __getnewargs__(self, /) -> tuple[Any, ...]:
        """..."""

        if not self._is_unset:
            return (True,)

        return ()

    def __getstate__(self, /) -> None:
        """..."""

        return None

    def __repr__(self, /) -> str:
        """..."""

        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        is_set = not self._is_unset

        object_repr = f"{cls_repr}(is_set={is_set!r})"

        if is_set:
            extra = "set"
        else:
            extra = f"unset, waiting={len(self._waiters)}"

        return f"<{object_repr} at {id(self):#x} [{extra}]>"

    def __bool__(self, /) -> bool:
        """..."""

        return not self._is_unset

    def __await__(self, /) -> Generator[Any, Any, bool]:
        """..."""

        if not self._is_unset:
            yield from async_checkpoint().__await__()

            self._wakeup()

            return True

        self._waiters.append(event := create_async_event())

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

        self._waiters.append(event := create_green_event())

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
        """..."""

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
                event.set()

                if _PERFECT_FAIRNESS_ENABLED:
                    try:
                        waiters.remove(event)
                    except ValueError:
                        pass

    @property
    def waiting(self, /) -> int:
        """..."""

        return len(self._waiters)


class REvent(Event):
    """..."""

    __slots__ = ("_timer",)

    def __new__(cls, /, is_set: bool = False) -> Self:
        """..."""

        self = object.__new__(cls)

        self._is_unset = Flag()

        if not is_set:
            self._is_unset.set()

        self._timer = count().__next__
        self._waiters = deque()

        return self

    @copies(Event.__getnewargs__)
    def __getnewargs__(self, /) -> tuple[Any, ...]:
        """..."""

        return Event.__getnewargs__(self)

    @copies(Event.__getstate__)
    def __getstate__(self, /) -> None:
        """..."""

        return Event.__getstate__(self)

    @copies(Event.__repr__)
    def __repr__(self, /) -> str:
        """..."""

        return Event.__repr__(self)

    @copies(Event.__bool__)
    def __bool__(self, /) -> bool:
        """..."""

        return Event.__bool__(self)

    def __await__(self, /) -> Generator[Any, Any, bool]:
        """..."""

        if not self._is_unset:
            yield from async_checkpoint().__await__()

            self._wakeup()

            return True

        self._waiters.append(
            token := [
                event := create_async_event(),
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
                event := create_green_event(),
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
        """..."""

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

                event.set()

                try:
                    waiters.remove(token)
                except ValueError:
                    pass

    @property
    @copies(Event.waiting.fget)
    def waiting(self, /) -> int:
        """..."""

        return Event.waiting.fget(self)


class CountdownEvent:
    """..."""

    __slots__ = (
        "__weakref__",
        "_is_unset",
        "_timer",
        "_waiters",
    )

    def __new__(cls, /, value: int | None = None) -> Self:
        """..."""

        if value is None:
            value = 0
        elif value < 0:
            msg = "value must be >= 0"
            raise ValueError(msg)

        self = object.__new__(cls)

        self._is_unset = [object()] * value
        self._timer = count().__next__
        self._waiters = deque()

        return self

    def __getnewargs__(self, /) -> tuple[Any, ...]:
        """..."""

        if value := len(self._is_unset):
            return (value,)

        return ()

    def __getstate__(self, /) -> None:
        """..."""

        return None

    def __repr__(self, /) -> str:
        """..."""

        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        value = len(self._is_unset)

        object_repr = f"{cls_repr}(value={value!r})"

        if value == 0:
            extra = f"value={value}"
        else:
            extra = f"value={value}, waiting={len(self._waiters)}"

        return f"<{object_repr} at {id(self):#x} [{extra}]>"

    def __bool__(self, /) -> bool:
        """..."""

        return not self._is_unset

    def __await__(self, /) -> Generator[Any, Any, bool]:
        """..."""

        if not self._is_unset:
            yield from async_checkpoint().__await__()

            self._wakeup()

            return True

        self._waiters.append(
            token := [
                event := create_async_event(),
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
                event := create_green_event(),
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
        default: object,
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

                event.set()

                try:
                    waiters.remove(token)
                except ValueError:
                    pass

    @property
    def value(self, /) -> int:
        """..."""

        return len(self._is_unset)

    @property
    def waiting(self, /) -> int:
        """..."""

        return len(self._waiters)
