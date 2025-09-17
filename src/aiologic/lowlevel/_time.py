#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

from . import _monkey


def _threading_sleep(seconds: float, /) -> None:
    global _threading_sleep

    _threading_sleep = _monkey._import_original("time", "sleep")

    _threading_sleep(seconds)


def _eventlet_sleep(seconds: float = 0, /) -> None:
    global _eventlet_sleep

    from eventlet import sleep as _eventlet_sleep

    _eventlet_sleep(seconds)


def _gevent_sleep(seconds: float = 0, /) -> None:
    global _gevent_sleep

    from gevent import sleep as _gevent_sleep

    _gevent_sleep(seconds)


async def _asyncio_sleep(seconds: float, /) -> None:
    global _asyncio_sleep

    from asyncio import sleep as _asyncio_sleep

    await _asyncio_sleep(seconds)


async def _curio_sleep(seconds: float, /) -> None:
    global _curio_sleep

    from curio import sleep as _curio_sleep

    await _curio_sleep(seconds)
