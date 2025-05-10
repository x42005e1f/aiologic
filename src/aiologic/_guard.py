#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

try:
    from sys import _is_gil_enabled
except ImportError:
    GIL_ENABLED = True
else:
    GIL_ENABLED = _is_gil_enabled()

USE_DELATTR = GIL_ENABLED  # see gh-127266


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

        if USE_DELATTR:
            self.__unlocked = True
        else:
            self.__unlocked = [True]

        self.action = action

        return self

    def __getnewargs__(self, /):
        if (action := self.action) != "using":
            args = (action,)
        else:
            args = ()

        return args

    def __getstate__(self, /):
        return None

    def __repr__(self, /):
        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        return f"{cls_repr}({self.action!r})"

    def __bool__(self, /):
        try:
            return bool(self.__unlocked)
        except AttributeError:
            return False

    def __enter__(self, /):
        try:
            if USE_DELATTR:
                del self.__unlocked
            else:
                self.__unlocked.pop()
        except (AttributeError, IndexError):
            success = False
        else:
            success = True

        if not success:
            msg = f"another task is already {self.action} this resource"
            raise BusyResourceError(msg)

        return self

    def __exit__(self, /, exc_type, exc_value, traceback):
        if USE_DELATTR:
            self.__unlocked = True
        else:
            self.__unlocked.append(True)
