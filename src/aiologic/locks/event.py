#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

__all__ = (
    "Event",
    "REvent",
)

from itertools import count
from collections import deque

from aiologic.lowlevel import (
    Flag,
    AsyncEvent,
    GreenEvent,
    checkpoint,
    green_checkpoint,
)


class Event:
    __slots__ = (
        "__weakref__",
        "__waiters",
        "__is_unset",
    )

    @staticmethod
    def __new__(cls, /, is_set=False):
        self = super(Event, cls).__new__(cls)

        self.__waiters = deque()
        self.__is_unset = not is_set

        return self

    def __getnewargs__(self, /):
        if not self.__is_unset:
            args = (True,)
        else:
            args = ()

        return args

    def __repr__(self, /):
        return f"Event(is_set={not self.__is_unset})"

    def __bool__(self, /):
        return not self.__is_unset

    def __await__(self, /):
        rescheduled = False

        if self.__is_unset:
            self.__waiters.append(event := AsyncEvent())

            if self.__is_unset:
                success = False

                try:
                    success = yield from event.__await__()
                finally:
                    if not success:
                        try:
                            self.__waiters.remove(event)
                        except ValueError:
                            pass

                rescheduled = True
            else:
                success = True
        else:
            success = True

        if success:
            self.__wakeup()

        if not rescheduled:
            yield from checkpoint().__await__()

        return success

    def wait(self, /, timeout=None):
        rescheduled = False

        if self.__is_unset:
            self.__waiters.append(event := GreenEvent())

            if self.__is_unset:
                success = False

                try:
                    success = event.wait(timeout)
                finally:
                    if not success:
                        try:
                            self.__waiters.remove(event)
                        except ValueError:
                            pass

                rescheduled = True
            else:
                success = True
        else:
            success = True

        if success:
            self.__wakeup()

        if not rescheduled:
            green_checkpoint()

        return success

    def set(self, /):
        self.__is_unset = False
        self.__wakeup()

    def is_set(self, /):
        return not self.__is_unset

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


class REvent:
    __slots__ = (
        "__weakref__",
        "__waiters",
        "__is_unset",
        "__timer",
    )

    @staticmethod
    def __new__(cls, /, is_set=False):
        self = super(REvent, cls).__new__(cls)

        self.__waiters = deque()
        self.__is_unset = Flag()

        if not is_set:
            self.__is_unset.set()

        self.__timer = count().__next__

        return self

    def __getnewargs__(self, /):
        if not self.__is_unset:
            args = (True,)
        else:
            args = ()

        return args

    def __repr__(self, /):
        return f"REvent(is_set={not self.__is_unset})"

    def __bool__(self, /):
        return not self.__is_unset

    def __await__(self, /):
        token = None
        rescheduled = False

        if (marker := self.__is_unset.get(None)) is not None:
            self.__waiters.append(
                token := [
                    event := AsyncEvent(),
                    marker,
                    self.__timer(),
                    None,
                ]
            )

            if marker is self.__is_unset.get(None):
                success = False

                try:
                    success = yield from event.__await__()
                finally:
                    if not success:
                        try:
                            self.__waiters.remove(token)
                        except ValueError:
                            pass

                rescheduled = True
            else:
                success = True
        else:
            success = True

        if success:
            if token is not None:
                self.__wakeup(token[3])
            else:
                self.__wakeup()

        if not rescheduled:
            yield from checkpoint().__await__()

        return success

    def wait(self, /, timeout=None):
        token = None
        rescheduled = False

        if (marker := self.__is_unset.get(None)) is not None:
            self.__waiters.append(
                token := [
                    event := GreenEvent(),
                    marker,
                    self.__timer(),
                    None,
                ]
            )

            if marker is self.__is_unset.get(None):
                success = False

                try:
                    success = event.wait(timeout)
                finally:
                    if not success:
                        try:
                            self.__waiters.remove(token)
                        except ValueError:
                            pass

                rescheduled = True
            else:
                success = True
        else:
            success = True

        if success:
            if token is not None:
                self.__wakeup(token[3])
            else:
                self.__wakeup()

        if not rescheduled:
            green_checkpoint()

        return success

    def clear(self, /):
        self.__is_unset.set()

    def set(self, /):
        self.__is_unset.clear()
        self.__wakeup()

    def is_set(self, /):
        return not self.__is_unset

    def __wakeup(self, /, deadline=None):
        waiters = self.__waiters
        is_unset = self.__is_unset

        if deadline is None:
            deadline = self.__timer()

        while waiters:
            try:
                token = waiters[0]
            except IndexError:
                break
            else:
                event, marker, time, _ = token

                if time <= deadline and marker is not is_unset.get(None):
                    token[3] = deadline

                    event.set()

                    try:
                        waiters.remove(token)
                    except ValueError:
                        pass
                else:
                    break

    @property
    def waiting(self, /):
        return len(self.__waiters)
