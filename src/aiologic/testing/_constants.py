#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

from typing import Final

GREEN_PAIRS: Final[tuple[tuple[str, str], ...]] = (
    ("threading", "threading"),
    ("eventlet", "eventlet"),
    ("gevent", "gevent"),
)
ASYNC_PAIRS: Final[tuple[tuple[str, str], ...]] = (
    ("asyncio", "asyncio"),
    ("curio", "curio"),
    ("trio", "trio"),
    ("anyio", "asyncio"),
    ("anyio", "trio"),
)
