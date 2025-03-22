#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from sniffio import (
    AsyncLibraryNotFoundError,
    thread_local as current_async_library_tlocal,
)
from wrapt import when_imported

from ._threads import ThreadLocal


class GreenLibraryNotFoundError(RuntimeError):
    pass


class _NamedLocal(ThreadLocal):
    name = None


current_green_library_tlocal = _NamedLocal()


def _eventlet_running():
    return False


@when_imported("eventlet")
def _eventlet_running_hook(_):
    global _eventlet_running

    def _eventlet_running():
        global _eventlet_running

        from eventlet.hubs import _threadlocal

        def _eventlet_running():
            return getattr(_threadlocal, "hub", None) is not None

        return _eventlet_running()


def _gevent_running():
    return False


@when_imported("gevent")
def _gevent_running_hook(_):
    global _gevent_running

    def _gevent_running():
        global _gevent_running

        from gevent._hub_local import get_hub_if_exists

        def _gevent_running():
            return get_hub_if_exists() is not None

        return _gevent_running()


def _asyncio_running():
    return False


@when_imported("asyncio")
def _asyncio_running_hook(_):
    global _asyncio_running

    def _asyncio_running():
        global _asyncio_running

        from asyncio import _get_running_loop
        from sys import version_info

        is_builtin = _get_running_loop.__module__ == "_asyncio"

        if version_info >= (3, 12) and is_builtin:

            def _asyncio_running():
                return _get_running_loop() is not None

        else:
            from sniffio import current_async_library_cvar

            def _asyncio_running():
                return (
                    current_async_library_cvar.get() == "asyncio"
                    or _get_running_loop() is not None
                )

        return _asyncio_running()


def _curio_running():
    return False


@when_imported("curio")
def _curio_running_hook(_):
    global _curio_running

    def _curio_running():
        global _curio_running

        from curio.meta import curio_running as _curio_running

        return _curio_running()


def current_green_library(*, failsafe=False):
    if (name := current_green_library_tlocal.name) is not None:
        return name
    elif _gevent_running():
        return "gevent"
    elif _eventlet_running():
        return "eventlet"
    else:
        return "threading"


def current_async_library(*, failsafe=False):
    if (name := current_async_library_tlocal.name) is not None:
        return name
    elif _curio_running():
        return "curio"
    elif _asyncio_running():
        return "asyncio"
    elif failsafe:
        return None
    else:
        msg = "unknown async library, or not in async context"
        raise AsyncLibraryNotFoundError(msg)
