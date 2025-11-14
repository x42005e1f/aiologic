#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import os

from itertools import count, islice
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
from .meta import DEFAULT, DefaultType, copies

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

_USE_ONCELOCK: Final[bool] = _PERFECT_FAIRNESS_ENABLED and not __GIL_ENABLED
_USE_ONCELOCK_FORCED: Final[bool] = not __GIL_ENABLED


class BrokenBarrierError(RuntimeError):
    """..."""


class Latch:
    """..."""

    __slots__ = (
        "__weakref__",
        "_filling",
        "_parties",
        "_unbroken",
        "_waiters",
    )

    def __new__(cls, /, parties: int | DefaultType = DEFAULT) -> Self:
        """..."""

        if parties is DEFAULT:
            parties = 0
        elif parties < 0:
            msg = "parties must be >= 0"
            raise ValueError(msg)

        self = object.__new__(cls)

        self._parties = parties

        self._filling = [None]
        self._unbroken = True

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
            >>> orig = Latch(4)
            >>> orig.parties
            4
            >>> copy = Latch(*orig.__getnewargs__())
            >>> copy.parties
            4
        """

        parties = self._parties

        if parties != 0:
            return (parties,)

        return ()

    def __getstate__(self, /) -> None:
        """
        Disables the use of internal state for pickling and copying.
        """

        return None

    def __copy__(self, /) -> Self:
        """..."""

        return self.__class__(self._parties)

    def __repr__(self, /) -> str:
        """..."""

        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        parties = self._parties

        if parties == 0:
            object_repr = f"{cls_repr}()"
        else:
            object_repr = f"{cls_repr}({parties!r})"

        waiting = len(self._waiters)

        if self._filling:
            extra = f"filling, waiting={waiting}"
        elif self._unbroken:
            extra = "draining"
        else:
            extra = "broken"

        return f"<{object_repr} at {id(self):#x} [{extra}]>"

    def __bool__(self, /) -> bool:
        """
        Returns :data:`True` if the barrier has been passed or broken.

        Used by the standard :ref:`truth testing procedure <truth>`.

        Example:
            >>> started = Latch(1)  # barrier is filling
            >>> bool(started)
            False
            >>> started.wait()  # barrier is draining
            >>> bool(started)
            True
            >>> started.abort()  # barrier is broken
            >>> bool(started)
            True
        """

        return not self._filling

    def __await__(self, /) -> Generator[Any, Any]:
        """..."""

        if not self._filling:
            unbroken = self._unbroken

            yield from async_checkpoint().__await__()

            self._wakeup(unbroken)

            if unbroken:
                return

            raise BrokenBarrierError

        self._waiters.append(
            token := [
                event := create_async_event(locking=_USE_ONCELOCK),
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
        """..."""

        if not self._filling:
            unbroken = self._unbroken

            green_checkpoint()

            self._wakeup(unbroken)

            if unbroken:
                return

            raise BrokenBarrierError

        self._waiters.append(
            token := [
                event := create_green_event(locking=_USE_ONCELOCK),
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
        """..."""

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

                remove = event.set()

                if _PERFECT_FAIRNESS_ENABLED:
                    try:
                        if remove or waiters[0] is token:
                            if _USE_ONCELOCK:
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
    def parties(self, /) -> int:
        """
        The initial number of tasks required to pass the barrier.
        """

        return self._parties

    @property
    def broken(self, /) -> bool:
        """
        A boolean that is :data:`True` if the barrier is in the broken state.
        """

        return not self._unbroken

    @property
    def waiting(self, /) -> int:
        """
        The current number of tasks waiting to pass.

        It represents the length of the waiting queue and thus changes
        immediately.
        """

        return len(self._waiters)


class Barrier:
    """..."""

    __slots__ = (
        "__weakref__",
        "_parties",
        "_unbroken",
        "_unlocked",
        "_waiters",
    )

    def __new__(cls, /, parties: int | DefaultType = DEFAULT) -> Self:
        """..."""

        if parties is DEFAULT:
            parties = 0
        elif parties < 0:
            msg = "parties must be >= 0"
            raise ValueError(msg)

        self = object.__new__(cls)

        self._parties = parties

        self._unbroken = True
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
            >>> orig = Barrier(4)
            >>> orig.parties
            4
            >>> copy = Barrier(*orig.__getnewargs__())
            >>> copy.parties
            4
        """

        parties = self._parties

        if parties != 0:
            return (parties,)

        return ()

    def __getstate__(self, /) -> None:
        """
        Disables the use of internal state for pickling and copying.
        """

        return None

    def __copy__(self, /) -> Self:
        """..."""

        return self.__class__(self._parties)

    def __repr__(self, /) -> str:
        """..."""

        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        parties = self._parties

        if parties == 0:
            object_repr = f"{cls_repr}()"
        else:
            object_repr = f"{cls_repr}({parties!r})"

        waiting = len(self._waiters)

        if not self._unbroken:
            extra = "broken"
        elif waiting >= self._parties > 0:
            extra = "draining"
        else:
            extra = f"filling, waiting={waiting}"

        return f"<{object_repr} at {id(self):#x} [{extra}]>"

    async def __aenter__(self, /) -> int:
        """..."""

        return await self

    def __enter__(self, /) -> int:
        """..."""

        return self.wait()

    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """..."""

        if exc_value is not None:
            self.abort()

    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """..."""

        if exc_value is not None:
            self.abort()

    def __await__(self, /) -> Generator[Any, Any, int]:
        """..."""

        if not self._unbroken:
            yield from async_checkpoint().__await__()

            self._wakeup_on_breaking()

            raise BrokenBarrierError

        self._waiters.append(
            token := [
                event := create_async_event(locking=_USE_ONCELOCK_FORCED),
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
            if _PERFECT_FAIRNESS_ENABLED:
                self._wakeup_on_draining_pf(token[1])
            else:
                self._wakeup_on_draining(token[1])
        else:
            self._wakeup_on_breaking()

            raise BrokenBarrierError

        return index

    def wait(self, /, timeout: float | None = None) -> int:
        """..."""

        if not self._unbroken:
            green_checkpoint()

            self._wakeup_on_breaking()

            raise BrokenBarrierError

        self._waiters.append(
            token := [
                event := create_green_event(locking=_USE_ONCELOCK_FORCED),
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
            if _PERFECT_FAIRNESS_ENABLED:
                self._wakeup_on_draining_pf(token[1])
            else:
                self._wakeup_on_draining(token[1])
        else:
            self._wakeup_on_breaking()

            raise BrokenBarrierError

        return index

    def abort(self, /) -> None:
        """..."""

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
            if not self._unbroken:
                return False

            tokens = [None] * parties

            for i in range(parties - 1, -1, -1):
                try:
                    token = waiters[i]
                except IndexError:
                    return False
                else:
                    tokens[i] = token
        else:
            if len(tokens) < parties:
                return False

        if not self._unbroken:
            return False

        if _PERFECT_FAIRNESS_ENABLED:
            tokens_marker = object()

            for i, token in enumerate(tokens):
                token[1] = tokens_marker
                token[2] = i

            self._wakeup_on_draining_pf(tokens_marker)
        else:
            tokens.reverse()

            for i, token in enumerate(tokens[::-1]):
                token[1] = tokens
                token[2] = i

                try:
                    waiters.remove(token)
                except ValueError:
                    pass

            self._wakeup_on_draining(tokens)

        return True

    def _wakeup_on_draining_pf(self, /, tokens_marker: object) -> None:
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

    def _wakeup_on_draining(self, /, tokens: list[Any]) -> None:
        while tokens:
            try:
                event, _, _ = tokens.pop()
            except IndexError:
                break
            else:
                event.set()

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

                remove = event.set()

                if _PERFECT_FAIRNESS_ENABLED:
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

    def _release(self, /) -> None:
        while True:
            self._unlocked.append(None)

            if self._acquire_nowait_if_reached():
                self._wakeup()
            else:
                break

    @property
    def parties(self, /) -> int:
        """
        The initial number of tasks required to pass the barrier.
        """

        return self._parties

    @property
    def broken(self, /) -> bool:
        """
        A boolean that is :data:`True` if the barrier is in the broken state.
        """

        return not self._unbroken

    @property
    def waiting(self, /) -> int:
        """
        The current number of tasks waiting to pass.

        It represents the length of the waiting queue and thus changes
        immediately.
        """

        return len(self._waiters)


class RBarrier(Barrier):
    """..."""

    __slots__ = (
        "_resetting",
        "_timer",
    )

    def __new__(cls, /, parties: int | DefaultType = DEFAULT) -> Self:
        """..."""

        if parties is DEFAULT:
            parties = 0
        elif parties < 0:
            msg = "parties must be >= 0"
            raise ValueError(msg)

        self = object.__new__(cls)

        self._parties = parties

        self._resetting = []
        self._timer = count().__next__
        self._unbroken = Flag(object())
        self._unlocked = [None]

        self._waiters = lazydeque()

        return self

    @copies(Barrier.__getnewargs__)
    def __getnewargs__(self, /) -> tuple[Any, ...]:
        """
        Returns arguments that can be used to create new instances with the
        same initial values.

        Used by:

        * The :mod:`pickle` module for pickling.
        * The :mod:`copy` module for copying.

        The current state does not affect the arguments.

        Example:
            >>> orig = RBarrier(4)
            >>> orig.parties
            4
            >>> copy = RBarrier(*orig.__getnewargs__())
            >>> copy.parties
            4
        """

        return Barrier.__getnewargs__(self)

    @copies(Barrier.__getstate__)
    def __getstate__(self, /) -> None:
        """
        Disables the use of internal state for pickling and copying.
        """

        return Barrier.__getstate__(self)

    @copies(Barrier.__copy__)
    def __copy__(self, /) -> Self:
        """..."""

        return Barrier.__copy__(self)

    def __repr__(self, /) -> str:
        """..."""

        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        object_repr = f"{cls_repr}({self._parties!r})"

        waiting = len(self._waiters)

        if self._resetting:
            extra = "resetting"
        elif not self._unbroken:
            extra = "broken"
        elif waiting >= self._parties > 0:
            extra = "draining"
        else:
            extra = f"filling, waiting={waiting}"

        return f"<{object_repr} at {id(self):#x} [{extra}]>"

    @copies(Barrier.__aenter__)
    async def __aenter__(self, /) -> int:
        """..."""

        return await Barrier.__aenter__(self)

    @copies(Barrier.__enter__)
    def __enter__(self, /) -> int:
        """..."""

        return Barrier.__enter__(self)

    @copies(Barrier.__aexit__)
    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """..."""

        return await Barrier.__aexit__(self, exc_type, exc_value, traceback)

    @copies(Barrier.__exit__)
    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """..."""

        return Barrier.__exit__(self, exc_type, exc_value, traceback)

    def __await__(self, /) -> Generator[Any, Any, int]:
        """..."""

        if not self._unbroken:
            yield from async_checkpoint().__await__()

            self._wakeup_on_breaking()

            raise BrokenBarrierError

        self._waiters.append(
            token := [
                event := create_async_event(locking=_USE_ONCELOCK_FORCED),
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
            if _PERFECT_FAIRNESS_ENABLED:
                self._wakeup_on_draining_pf(token[1])
            else:
                self._wakeup_on_draining(token[1])
        else:
            self._wakeup_on_breaking(token[3])

            raise BrokenBarrierError

        return index

    def wait(self, /, timeout: float | None = None) -> int:
        """..."""

        if not self._unbroken:
            green_checkpoint()

            self._wakeup_on_breaking()

            raise BrokenBarrierError

        self._waiters.append(
            token := [
                event := create_green_event(locking=_USE_ONCELOCK_FORCED),
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
            if _PERFECT_FAIRNESS_ENABLED:
                self._wakeup_on_draining_pf(token[1])
            else:
                self._wakeup_on_draining(token[1])
        else:
            self._wakeup_on_breaking(token[3])

            raise BrokenBarrierError

        return index

    def reset(self, /) -> None:
        """..."""

        self._resetting.append(None)

        try:
            self._unbroken.clear()

            self._wakeup_on_breaking()

            self._unbroken.set()
        finally:
            self._resetting.pop()

    def abort(self, /) -> None:
        """..."""

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
            if self._unbroken.get(None) is not marker:
                return False

            tokens = [None] * parties

            for i in range(parties - 1, -1, -1):
                try:
                    token = waiters[i]
                except IndexError:
                    return False
                else:
                    tokens[i] = token

            if len({token[0] for token in tokens}) < parties:
                return False
        else:
            if len(tokens) < parties:
                return False

        if self._unbroken.get(None) is not marker:
            return False

        if invalid_tokens := [
            token for token in tokens if token[1] is not marker
        ]:
            for token in invalid_tokens:
                token[0].set()

                try:
                    waiters.remove(token)
                except ValueError:
                    pass

            return False

        if _PERFECT_FAIRNESS_ENABLED:
            tokens_marker = object()

            for i, token in enumerate(tokens):
                token[1] = tokens_marker
                token[4] = i

            self._wakeup_on_draining_pf(tokens_marker)
        else:
            tokens.reverse()

            for i, token in enumerate(tokens[::-1]):
                token[1] = tokens
                token[4] = i

                try:
                    waiters.remove(token)
                except ValueError:
                    pass

            self._wakeup_on_draining(tokens)

        return True

    def _wakeup_on_draining_pf(self, /, tokens_marker: object) -> None:
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

    def _wakeup_on_draining(self, /, tokens: list[Any]) -> None:
        while tokens:
            try:
                event, _, _, _, _ = tokens.pop()
            except IndexError:
                break
            else:
                event.set()

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
    @copies(Barrier.parties.fget)
    def parties(self, /) -> int:
        """
        The initial number of tasks required to pass the barrier.
        """

        return Barrier.parties.fget(self)

    @property
    @copies(Barrier.broken.fget)
    def broken(self, /) -> bool:
        """
        A boolean that is :data:`True` if the barrier is in the broken state.
        """

        return Barrier.broken.fget(self)

    @property
    @copies(Barrier.waiting.fget)
    def waiting(self, /) -> int:
        """
        The current number of tasks waiting to pass.

        It represents the length of the waiting queue and thus changes
        immediately.
        """

        return Barrier.waiting.fget(self)
