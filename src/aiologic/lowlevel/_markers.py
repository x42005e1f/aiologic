#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC


class MissingType:
    __slots__ = ()

    def __new__(cls, /):
        return MISSING

    def __init_subclass__(cls, /, **kwargs):
        bcs = MissingType
        bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

        msg = f"type '{bcs_repr}' is not an acceptable base type"
        raise TypeError(msg)

    def __reduce__(self, /):
        return "MISSING"

    def __repr__(self, /):
        return f"{self.__class__.__module__}.MISSING"

    def __bool__(self, /):
        return False


MISSING = object.__new__(MissingType)
