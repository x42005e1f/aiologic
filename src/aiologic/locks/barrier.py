#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

__all__ = (
    "BrokenBarrierError",
    "Latch",
    "Barrier",
)

from collections import deque

from aiologic.lowlevel import (
    Flag,
    AsyncEvent,
    GreenEvent,
    checkpoint,
    green_checkpoint,
)


class BrokenBarrierError(RuntimeError):
    pass


class Latch:
    __slots__ = (
        "__weakref__",
        "__waiters",
        "__reached",
        "parties",
    )

    @staticmethod
    def __new__(cls, /, parties):
        self = super(Latch, cls).__new__(cls)

        if parties < 1:
            raise ValueError("parties must be >= 1")

        self.__waiters = deque()
        self.__reached = Flag()

        self.parties = parties

        return self

    def __getnewargs__(self, /):
        return (self.parties,)

    def __repr__(self, /):
        return f"Latch({self.parties})"

    def __await__(self, /):
        reached = self.__reached
        rescheduled = False
        force_checkpoint = False

        try:
            if not reached:
                self.__waiters.append(event := AsyncEvent())

                if not reached:
                    if len(self.__waiters) < self.parties:
                        try:
                            rescheduled = yield from event.__await__()
                        finally:
                            if not rescheduled:
                                reached.set(False)
                    else:
                        force_checkpoint = reached.set(True)
        finally:
            self.__wakeup()

        if not reached.get(False):
            raise BrokenBarrierError

        if not rescheduled or force_checkpoint:
            yield from checkpoint(force=force_checkpoint).__await__()

    def wait(self, /, timeout=None):
        reached = self.__reached
        rescheduled = False
        force_checkpoint = False

        try:
            if not reached:
                self.__waiters.append(event := GreenEvent())

                if not reached:
                    if len(self.__waiters) < self.parties:
                        try:
                            rescheduled = event.wait(timeout)
                        finally:
                            if not rescheduled:
                                reached.set(False)
                    else:
                        force_checkpoint = reached.set(True)
        finally:
            self.__wakeup()

        if not reached.get(False):
            raise BrokenBarrierError

        if not rescheduled or force_checkpoint:
            green_checkpoint(force=force_checkpoint)

    def abort(self, /):
        self.__reached.set(False)
        self.__wakeup()

    def __wakeup(self, /):
        waiters = self.__waiters

        while waiters:
            try:
                event = waiters[0]
            except IndexError:
                break
            else:
                event.set()

                try:
                    waiters.remove(event)
                except ValueError:
                    pass

    @property
    def waiting(self, /):
        return len(self.__waiters)

    @property
    def broken(self, /):
        return not self.__reached.get(True)


class Barrier:
    __slots__ = (
        "__weakref__",
        "__waiters",
        "__unlocked",
        "__is_broken",
        "parties",
    )

    @staticmethod
    def __new__(cls, /, parties):
        self = super(Barrier, cls).__new__(cls)

        if parties < 1:
            raise ValueError("parties must be >= 1")

        self.__waiters = deque()
        self.__unlocked = [True]

        self.__is_broken = False

        self.parties = parties

        return self

    def __getnewargs__(self, /):
        return (self.parties,)

    def __repr__(self, /):
        return f"Barrier({self.parties})"

    def __acquire_nowait(self, /):
        if unlocked := self.__unlocked:
            try:
                unlocked.pop()
            except IndexError:
                success = False
            else:
                success = True
        else:
            success = False

        return success

    def __acquire_nowait_as_waiter(self, /, token):
        waiters = self.__waiters
        parties = self.parties

        try:
            if (
                len(waiters) >= parties
                and waiters[parties - 1] is token
                and (unlocked := self.__unlocked)
                and waiters[parties - 1] is token
                and not self.__is_broken
            ):
                try:
                    unlocked.pop()
                except IndexError:
                    success = False
                else:
                    success = True
            else:
                success = False
        except IndexError:
            success = False

        return success

    @staticmethod
    def __wakeup(tokens):
        while tokens:
            try:
                token = tokens[0]
            except IndexError:
                break
            else:
                event, cancelled, _, _, _ = token

                cancelled.set(False)
                event.set()

                try:
                    tokens.remove(token)
                except ValueError:
                    pass

    def __wakeup_as_waiter(self, /):
        waiters = self.__waiters
        parties = self.parties

        tokens = deque()

        for _ in range(parties):
            token = waiters.popleft()

            token[2] = len(tokens)
            token[3] = tokens
            token[4] = False

            tokens.append(token)

        self.__wakeup(tokens)

        return not token[1].get()

    def __release(self, /):
        waiters = self.__waiters
        parties = self.parties

        unlocked = self.__unlocked

        while not self.__is_broken:
            if len(waiters) >= parties:
                if self.__wakeup_as_waiter():
                    break
                else:
                    continue

            unlocked.append(True)

            if len(waiters) >= parties:
                if self.__acquire_nowait():
                    continue
                else:
                    break
            else:
                break
        else:
            self.__wakeup(waiters)

        if self.__is_broken and self.__acquire_nowait():
            self.__wakeup(waiters)

    def __await__(self, /):
        waiters = self.__waiters
        parties = self.parties

        is_broken = False
        rescheduled = False

        if not (is_broken := self.__is_broken):
            waiters.append(
                token := [
                    event := AsyncEvent(),
                    Flag(),
                    -1,
                    None,
                    True,
                ]
            )

            if not (is_broken := self.__is_broken):
                try:
                    if self.__acquire_nowait_as_waiter(token):
                        self.__wakeup_as_waiter()

                        yield from checkpoint(force=True).__await__()

                        rescheduled = True
                    else:
                        rescheduled = yield from event.__await__()
                finally:
                    if rescheduled or not token[1].set(True):
                        _, _, index, _, is_broken = token

                        if not is_broken and index + 1 == parties:
                            self.__release()
                    else:
                        self.abort()

        if is_broken:
            self.__wakeup(waiters)

            raise BrokenBarrierError

        if not rescheduled:
            yield from checkpoint().__await__()

        return index

    def wait(self, /, timeout=None):
        waiters = self.__waiters
        parties = self.parties

        is_broken = False
        rescheduled = False

        if not (is_broken := self.__is_broken):
            waiters.append(
                token := [
                    event := GreenEvent(),
                    Flag(),
                    -1,
                    None,
                    True,
                ]
            )

            if not (is_broken := self.__is_broken):
                try:
                    if self.__acquire_nowait_as_waiter(token):
                        self.__wakeup_as_waiter()

                        green_checkpoint(force=True)

                        rescheduled = True
                    else:
                        rescheduled = event.wait(timeout)
                finally:
                    if rescheduled or not token[1].set(True):
                        _, _, index, _, is_broken = token

                        if not is_broken and index + 1 == parties:
                            self.__release()
                    else:
                        self.abort()

        if is_broken:
            self.__wakeup(waiters)

            raise BrokenBarrierError

        if not rescheduled:
            green_checkpoint()

        return index

    def abort(self, /):
        self.__is_broken = True

        if self.__acquire_nowait():
            self.__wakeup(self.__waiters)

    @property
    def waiting(self, /):
        return len(self.__waiters)

    @property
    def broken(self, /):
        return self.__is_broken
