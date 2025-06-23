#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import os

from collections import deque
from itertools import count, islice
from typing import TYPE_CHECKING, Any, Final

from ._flag import Flag
from .lowlevel import (
    async_checkpoint,
    create_async_event,
    create_green_event,
    green_checkpoint,
)

if TYPE_CHECKING:
    import sys

    from types import TracebackType

    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self

    if sys.version_info >= (3, 9):
        from collections.abc import Generator
    else:
        from typing import Generator

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


class BrokenBarrierError(RuntimeError):
    pass


class Latch:
    __slots__ = (
        "__weakref__",
        "_filling",
        "_parties",
        "_unbroken",
        "_waiters",
    )

    def __new__(cls, /, parties: int | None = None) -> Self:
        if parties is None:
            parties = 1
        elif parties < 0:
            msg = "parties must be >= 0"
            raise ValueError(msg)

        self = object.__new__(cls)

        self._parties = parties

        self._filling = [None]
        self._unbroken = True

        self._waiters = deque()

        return self

    def __getnewargs__(self, /) -> tuple[Any, ...]:
        return (self._parties,)

    def __getstate__(self, /) -> None:
        return None

    def __repr__(self, /) -> str:
        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        object_repr = f"{cls_repr}({self._parties!r})"

        waiting = len(self._waiters)

        if self._filling:
            extra = f"filling, waiting={waiting}"
        elif self._unbroken:
            extra = "draining"
        else:
            extra = "broken"

        return f"<{object_repr} at {id(self):#x} [{extra}]>"

    def __bool__(self, /) -> bool:
        return not self._filling

    def __await__(self, /) -> Generator[Any, Any, None]:
        if not self._filling:
            unbroken = self._unbroken

            yield from async_checkpoint().__await__()

            self._wakeup(unbroken)

            if unbroken:
                return

            raise BrokenBarrierError

        self._waiters.append(
            token := [
                event := create_async_event(),
                self._unbroken,
            ]
        )

        if not self._filling:
            if event.set():
                try:
                    self._waiters.remove(event)
                except ValueError:
                    pass

        event.force = self._wakeup_if_reached()

        success = False

        try:
            success = yield from event.__await__()
        finally:
            if not success:
                self.abort()

        unbroken = token[1]

        if not unbroken:
            raise BrokenBarrierError

        self._wakeup(unbroken)

    def wait(self, /, timeout: float | None = None) -> None:
        if not self._filling:
            unbroken = self._unbroken

            green_checkpoint()

            self._wakeup(unbroken)

            if unbroken:
                return

            raise BrokenBarrierError

        self._waiters.append(
            token := [
                event := create_green_event(),
                self._unbroken,
            ]
        )

        if not self._filling:
            if event.set():
                try:
                    self._waiters.remove(event)
                except ValueError:
                    pass

        event.force = self._wakeup_if_reached()

        success = False

        try:
            success = event.wait(timeout)
        finally:
            if not success:
                self.abort()

        unbroken = token[1]

        if not unbroken:
            raise BrokenBarrierError

        self._wakeup(unbroken)

    def abort(self, /) -> None:
        self._unbroken = False

        if self._filling:
            try:
                self._filling.pop()
            except IndexError:
                pass

        self._wakeup(False)

    def _wakeup_if_reached(self, /) -> bool:
        if self._filling:
            if len(self._waiters) >= self._parties > 0:
                try:
                    self._filling.pop()
                except IndexError:
                    return False
                else:
                    if len(self._waiters) >= self._parties > 0:
                        self._wakeup(True)

                    return True

        return False

    def _wakeup(self, /, unbroken: bool) -> None:
        waiters = self._waiters

        while waiters:
            try:
                if _PERFECT_FAIRNESS_ENABLED:
                    token = waiters[0]
                else:
                    token = waiters.popleft()
            except IndexError:
                break
            else:
                event, _ = token

                token[1] = unbroken

                event.set()

                if _PERFECT_FAIRNESS_ENABLED:
                    try:
                        waiters.remove(token)
                    except ValueError:
                        pass

    @property
    def parties(self, /) -> int:
        return self._parties

    @property
    def broken(self, /) -> bool:
        return not self._unbroken

    @property
    def waiting(self, /) -> int:
        return len(self._waiters)


class Barrier:
    __slots__ = (
        "__weakref__",
        "_parties",
        "_unbroken",
        "_unlocked",
        "_waiters",
    )

    def __new__(cls, /, parties: int | None = None) -> Self:
        if parties is None:
            parties = 1
        elif parties < 0:
            msg = "parties must be >= 0"
            raise ValueError(msg)

        self = object.__new__(cls)

        self._parties = parties

        self._unbroken = True
        self._unlocked = [None]

        self._waiters = deque()

        return self

    def __getnewargs__(self, /) -> tuple[Any, ...]:
        return (self._parties,)

    def __getstate__(self, /) -> None:
        return None

    def __repr__(self, /) -> str:
        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        object_repr = f"{cls_repr}({self._parties!r})"

        waiting = len(self._waiters)

        if not self._unbroken:
            extra = "broken"
        elif waiting >= self._parties:
            extra = "draining"
        else:
            extra = f"filling, waiting={waiting}"

        return f"<{object_repr} at {id(self):#x} [{extra}]>"

    async def __aenter__(self, /) -> int:
        return await self

    def __enter__(self, /) -> int:
        return self.wait()

    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_value is not None:
            self.abort()

    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_value is not None:
            self.abort()

    def __await__(self, /) -> Generator[Any, Any, int]:
        if not self._unbroken:
            yield from async_checkpoint().__await__()

            self._wakeup_on_breaking()

            raise BrokenBarrierError

        self._waiters.append(
            token := [
                event := create_async_event(),
                None,
                -1,
            ]
        )

        if not self._unbroken:
            if event.set():
                try:
                    self._waiters.remove(token)
                except ValueError:
                    pass

        event.force = self._wakeup_if_reached()

        success = False

        try:
            success = yield from event.__await__()
        finally:
            if not success:
                self.abort()

        index = token[2]

        if index >= 0:
            self._wakeup_on_draining(token[1])
        else:
            self._wakeup_on_breaking()

            raise BrokenBarrierError

        return index

    def wait(self, /, timeout: float | None = None) -> int:
        if not self._unbroken:
            green_checkpoint()

            self._wakeup_on_breaking()

            raise BrokenBarrierError

        self._waiters.append(
            token := [
                event := create_green_event(),
                None,
                -1,
            ]
        )

        if not self._unbroken:
            if event.set():
                try:
                    self._waiters.remove(token)
                except ValueError:
                    pass

        event.force = self._wakeup_if_reached()

        success = False

        try:
            success = event.wait(timeout)
        finally:
            if not success:
                self.abort()

        index = token[2]

        if index >= 0:
            self._wakeup_on_draining(token[1])
        else:
            self._wakeup_on_breaking()

            raise BrokenBarrierError

        return index

    def abort(self, /) -> None:
        self._unbroken = False

        self._wakeup_on_breaking()

    def _acquire_nowait_if_reached(self, /) -> bool:
        while self._unlocked:
            if self._unbroken and len(self._waiters) >= self._parties > 0:
                try:
                    self._unlocked.pop()
                except IndexError:
                    return False
                else:
                    if self._unbroken and (
                        len(self._waiters) >= self._parties > 0
                    ):
                        return True

                    self._unlocked.append(None)
            else:
                return False

        return False

    def _wakeup_if_reached(self, /) -> bool:
        if self._acquire_nowait_if_reached():
            try:
                return self._wakeup()
            finally:
                self._release()

        return False

    def _wakeup(self, /) -> bool:
        parties = self._parties
        waiters = self._waiters

        if not self._unbroken:
            return False

        try:
            tokens = list(islice(waiters, parties))
        except RuntimeError:  # deque mutated during iteration
            tokens = [None] * parties

            for i in range(parties):
                try:
                    token = waiters[i]
                except IndexError:
                    return False
                else:
                    tokens[i] = token

        if len(tokens) < parties:
            return False

        if not self._unbroken:
            return False

        tokens_marker = object()

        for i, token in enumerate(tokens):
            token[1] = tokens_marker
            token[2] = i

        self._wakeup_on_draining(tokens_marker)

        return True

    def _wakeup_on_draining(self, /, tokens_marker: object) -> None:
        waiters = self._waiters

        while waiters:
            try:
                token = waiters[0]
            except IndexError:
                break
            else:
                event, marker, _ = token

                if marker is not tokens_marker:
                    break

                event.set()

                try:
                    waiters.remove(token)
                except ValueError:
                    pass

    def _wakeup_on_breaking(self, /) -> None:
        waiters = self._waiters

        while waiters:
            try:
                if _PERFECT_FAIRNESS_ENABLED:
                    token = waiters[0]
                else:
                    token = waiters.popleft()
            except IndexError:
                break
            else:
                event, _, _ = token

                event.set()

                if _PERFECT_FAIRNESS_ENABLED:
                    try:
                        waiters.remove(token)
                    except ValueError:
                        pass

    def _release(self, /) -> None:
        while True:
            self._unlocked.append(None)

            if self._acquire_nowait_if_reached():
                self._wakeup()
            else:
                break

    @property
    def parties(self, /) -> int:
        return self._parties

    @property
    def broken(self, /) -> bool:
        return not self._unbroken

    @property
    def waiting(self, /) -> int:
        return len(self._waiters)


class RBarrier(Barrier):
    __slots__ = (
        "_resetting",
        "_timer",
    )

    def __new__(cls, /, parties: int | None = None) -> Self:
        if parties is None:
            parties = 1
        elif parties < 0:
            msg = "parties must be >= 0"
            raise ValueError(msg)

        self = object.__new__(cls)

        self._parties = parties

        self._resetting = []
        self._timer = count().__next__
        self._unbroken = Flag(object())
        self._unlocked = [None]

        self._waiters = deque()

        return self

    def __repr__(self, /) -> str:
        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        object_repr = f"{cls_repr}({self._parties!r})"

        waiting = len(self._waiters)

        if self._resetting:
            extra = "resetting"
        elif not self._unbroken:
            extra = "broken"
        elif waiting >= self._parties:
            extra = "draining"
        else:
            extra = f"filling, waiting={waiting}"

        return f"<{object_repr} at {id(self):#x} [{extra}]>"

    def __await__(self, /) -> Generator[Any, Any, int]:
        if not self._unbroken:
            yield from async_checkpoint().__await__()

            self._wakeup_on_breaking()

            raise BrokenBarrierError

        self._waiters.append(
            token := [
                event := create_async_event(),
                marker := self._unbroken.get(default_factory=object),
                self._timer(),
                None,
                -1,
            ]
        )

        if self._unbroken.get(None) is not marker:
            if event.set():
                try:
                    self._waiters.remove(token)
                except ValueError:
                    pass

        event.force = self._wakeup_if_reached()

        success = False

        try:
            success = yield from event.__await__()
        finally:
            if not success:
                self.abort()

        index = token[4]

        if index >= 0:
            self._wakeup_on_draining(token[1])
        else:
            self._wakeup_on_breaking(token[3])

            raise BrokenBarrierError

        return index

    def wait(self, /, timeout: float | None = None) -> int:
        if not self._unbroken:
            green_checkpoint()

            self._wakeup_on_breaking()

            raise BrokenBarrierError

        self._waiters.append(
            token := [
                event := create_green_event(),
                marker := self._unbroken.get(default_factory=object),
                self._timer(),
                None,
                -1,
            ]
        )

        if self._unbroken.get(None) is not marker:
            if event.set():
                try:
                    self._waiters.remove(token)
                except ValueError:
                    pass

        event.force = self._wakeup_if_reached()

        success = False

        try:
            success = event.wait(timeout)
        finally:
            if not success:
                self.abort()

        index = token[4]

        if index >= 0:
            self._wakeup_on_draining(token[1])
        else:
            self._wakeup_on_breaking(token[3])

            raise BrokenBarrierError

        return index

    def reset(self, /) -> None:
        self._resetting.append(None)

        try:
            self._unbroken.clear()
            self._unbroken.set()

            self._wakeup_on_breaking()
        finally:
            self._resetting.pop()

        self._wakeup_if_reached()

    def abort(self, /) -> None:
        self._unbroken.clear()

        self._wakeup_on_breaking()

    def _wakeup(self, /) -> bool:
        parties = self._parties
        waiters = self._waiters

        try:
            marker = self._unbroken.get()
        except LookupError:
            return False

        try:
            tokens = list(islice(waiters, parties))
        except RuntimeError:  # deque mutated during iteration
            tokens = [None] * parties

            for i in range(parties):
                try:
                    token = waiters[i]
                except IndexError:
                    return False
                else:
                    tokens[i] = token

        if len(tokens) < parties:
            return False

        if self._unbroken.get(None) is not marker:
            return False

        tokens_marker = object()

        for i, token in enumerate(tokens):
            token[1] = tokens_marker
            token[4] = i

        self._wakeup_on_draining(tokens_marker)

        return True

    def _wakeup_on_draining(self, /, tokens_marker: object) -> None:
        waiters = self._waiters

        while waiters:
            try:
                token = waiters[0]
            except IndexError:
                break
            else:
                event, marker, _, _, _ = token

                if marker is not tokens_marker:
                    break

                event.set()

                try:
                    waiters.remove(token)
                except ValueError:
                    pass

    def _wakeup_on_breaking(self, /, deadline: float | None = None) -> None:
        waiters = self._waiters

        while waiters:
            try:
                token = waiters[0]
            except IndexError:
                break
            else:
                event, marker, time, _, _ = token

                if deadline is None:
                    deadline = self._timer()

                if time > deadline:
                    break

                if self._unbroken.get(None) is marker:
                    break

                token[3] = deadline

                event.set()

                try:
                    waiters.remove(token)
                except ValueError:
                    pass
