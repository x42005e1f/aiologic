#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC


def _threading_sleep(seconds):
    global _threading_sleep

    from . import _monkey

    if _monkey._eventlet_patched("time"):
        _threading_sleep = _monkey._import_eventlet_original("time").sleep
    elif _monkey._gevent_patched("time"):
        _threading_sleep = _monkey._import_gevent_original("time").sleep
    else:
        time_sleep = _monkey._import_python_original("time").sleep

        if _monkey._eventlet_patched("time"):
            _threading_sleep = _monkey._import_eventlet_original("time").sleep
        elif _monkey._gevent_patched("time"):
            _threading_sleep = _monkey._import_gevent_original("time").sleep
        else:
            _threading_sleep = time_sleep

    _threading_sleep(seconds)


def _eventlet_sleep(seconds=0):
    global _eventlet_sleep

    from eventlet import sleep as _eventlet_sleep

    _eventlet_sleep(seconds)


def _gevent_sleep(seconds=0):
    global _gevent_sleep

    from gevent import sleep as _gevent_sleep

    _gevent_sleep(seconds)


async def _asyncio_sleep(seconds):
    global _asyncio_sleep

    from asyncio import sleep as _asyncio_sleep

    await _asyncio_sleep(seconds)


async def _curio_sleep(seconds):
    global _curio_sleep

    from curio import sleep as _curio_sleep

    await _curio_sleep(seconds)
