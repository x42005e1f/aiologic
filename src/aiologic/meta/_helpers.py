#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sys

    from typing import TypeVar

    if sys.version_info >= (3, 9):  # PEP 585
        from collections.abc import Awaitable
    else:
        from typing import Awaitable

    _T = TypeVar("_T")


async def await_for(awaitable: Awaitable[_T], /) -> _T:
    """
    Wait for *awaitable* to complete.

    Useful when you need to schedule waiting for an awaitable primitive via a
    function that only accepts asynchronous functions.
    """

    return await awaitable
