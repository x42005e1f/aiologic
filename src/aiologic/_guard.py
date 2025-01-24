#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC


class BusyResourceError(RuntimeError):
    pass


class ResourceGuard:
    __slots__ = (
        "__unlocked",
        "__weakref__",
        "action",
    )

    def __new__(cls, /, action="using"):
        self = super().__new__(cls)

        self.__unlocked = [True]

        self.action = action

        return self

    def __getnewargs__(self, /):
        if (action := self.action) != "using":
            args = (action,)
        else:
            args = ()

        return args

    def __repr__(self, /):
        return f"ResourceGuard({self.action!r})"

    def __bool__(self, /):
        return bool(self.__unlocked)

    def __enter__(self, /):
        try:
            self.__unlocked.pop()
        except IndexError:
            success = False
        else:
            success = True

        if not success:
            msg = f"another task is already {self.action} this resource"
            raise BusyResourceError(msg)

        return self

    def __exit__(self, /, exc_type, exc_value, traceback):
        self.__unlocked.append(True)
