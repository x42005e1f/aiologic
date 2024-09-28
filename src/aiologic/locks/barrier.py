#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

__all__ = (
    "BrokenBarrierError",
    "Latch",
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
                        reached.set(True)
        finally:
            self.__wakeup()

        if not reached.get(False):
            raise BrokenBarrierError

        if not rescheduled:
            green_checkpoint()

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
