#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from typing import TypeVar

if sys.version_info >= (3, 9):  # PEP 585
    from collections.abc import Awaitable
else:
    from typing import Awaitable

_T = TypeVar("_T")

async def await_for(awaitable: Awaitable[_T], /) -> _T: ...
