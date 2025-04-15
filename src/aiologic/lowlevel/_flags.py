#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys
import types

from ._markers import MISSING


class Flag:
    __slots__ = ("__markers",)

    def __new__(cls, /, marker=MISSING):
        self = super().__new__(cls)

        if marker is not MISSING:
            self.__markers = [marker]
        else:
            self.__markers = []

        return self

    def __getnewargs__(self, /):
        if self.__markers:
            try:
                return (self.__markers[0],)
            except IndexError:
                pass

        return ()

    def __repr__(self, /):
        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        if self.__markers:
            try:
                return f"{cls_repr}({self.__markers[0]!r})"
            except IndexError:
                pass

        return f"{cls_repr}()"

    def __bool__(self, /):
        return bool(self.__markers)

    def get(self, /, default=MISSING, *, default_factory=MISSING):
        if self.__markers:
            try:
                return self.__markers[0]
            except IndexError:
                pass

        if default is not MISSING:
            return default

        if default_factory is not MISSING:
            return default_factory()

        raise LookupError(self)

    def set(self, /, marker=MISSING):
        markers = self.__markers

        if not markers:
            if marker is MISSING:
                marker = object()

            markers.append(marker)

            if len(markers) > 1:
                del markers[1:]

        if marker is not MISSING:
            try:
                return marker is markers[0]
            except IndexError:
                pass

        return False

    def clear(self, /):
        self.__markers.clear()

    if sys.version_info >= (3, 9):
        __class_getitem__ = classmethod(types.GenericAlias)
