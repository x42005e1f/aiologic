#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from typing import TypeVar

import aiologic

_T = TypeVar("_T")

class Flag(aiologic.lowlevel.Flag[_T]):
    __slots__ = ("__weakref__",)
