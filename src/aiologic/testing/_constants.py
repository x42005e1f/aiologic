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
GREEN_LIBRARIES: Final[tuple[str, ...]] = tuple(
    dict.fromkeys(library for library, backend in GREEN_PAIRS)
)
ASYNC_LIBRARIES: Final[tuple[str, ...]] = tuple(
    dict.fromkeys(library for library, backend in ASYNC_PAIRS)
)
GREEN_BACKENDS: Final[tuple[str, ...]] = tuple(
    dict.fromkeys(backend for library, backend in GREEN_PAIRS)
)
ASYNC_BACKENDS: Final[tuple[str, ...]] = tuple(
    dict.fromkeys(backend for library, backend in ASYNC_PAIRS)
)
