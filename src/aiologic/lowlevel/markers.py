#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

__all__ = ("MISSING",)


class MissingType:
    __slots__ = ()

    @staticmethod
    def __new__(cls, /):
        if cls is MissingType:
            self = MISSING
        else:
            self = super(MissingType, cls).__new__(cls)

        return self

    @classmethod
    def __init_subclass__(cls, /, **kwargs):
        raise TypeError("type 'MissingType' is not an acceptable base type")

    def __reduce__(self, /):
        return "MISSING"

    def __repr__(self, /):
        return "MISSING"

    def __bool__(self, /):
        return False


MISSING = object.__new__(MissingType)
