#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, overload

from sniffio import (
    AsyncLibraryNotFoundError as AsyncLibraryNotFoundError,
    thread_local,
)
from wrapt import when_imported

from ._threads import _local
from ._utils import _replaces as replaces

if TYPE_CHECKING:
    from sniffio._impl import _ThreadLocal


class GreenLibraryNotFoundError(RuntimeError):
    pass


class _NamedLocal(_local):
    name: str | None = None


current_green_library_tlocal: _NamedLocal = _NamedLocal()
current_async_library_tlocal: _ThreadLocal = thread_local


def _eventlet_running() -> bool:
    return False


def _gevent_running() -> bool:
    return False


def _asyncio_running() -> bool:
    return False


def _curio_running() -> bool:
    return False


@when_imported("eventlet")
def _(_):
    global _eventlet_running

    @replaces(_eventlet_running)
    def _eventlet_running():
        global _eventlet_running

        from eventlet.hubs import _threadlocal

        @replaces(_eventlet_running)
        def _eventlet_running():
            return getattr(_threadlocal, "hub", None) is not None

        return _eventlet_running()


@when_imported("gevent")
def _(_):
    global _gevent_running

    @replaces(_gevent_running)
    def _gevent_running():
        global _gevent_running

        from gevent._hub_local import get_hub_if_exists

        @replaces(_gevent_running)
        def _gevent_running():
            return get_hub_if_exists() is not None

        return _gevent_running()


@when_imported("asyncio")
def _(_):
    global _asyncio_running

    @replaces(_asyncio_running)
    def _asyncio_running():
        global _asyncio_running

        from asyncio import _get_running_loop
        from sys import version_info

        is_builtin = _get_running_loop.__module__ == "_asyncio"

        if version_info >= (3, 12) and is_builtin:

            @replaces(_asyncio_running)
            def _asyncio_running():
                return _get_running_loop() is not None

        else:
            from sniffio import current_async_library_cvar

            @replaces(_asyncio_running)
            def _asyncio_running():
                return (
                    current_async_library_cvar.get() == "asyncio"
                    or _get_running_loop() is not None
                )

        return _asyncio_running()


@when_imported("curio")
def _(_):
    global _curio_running

    @replaces(_curio_running)
    def _curio_running():
        global _curio_running

        from curio.meta import curio_running as _curio_running

        return _curio_running()


@overload
def current_green_library(*, failsafe: Literal[False] = False) -> str: ...
@overload
def current_green_library(*, failsafe: Literal[True]) -> str | None: ...
def current_green_library(*, failsafe: bool = False) -> str | None:
    if (name := current_green_library_tlocal.name) is not None:
        return name

    if _gevent_running():
        return "gevent"

    if _eventlet_running():
        return "eventlet"

    return "threading"


@overload
def current_async_library(*, failsafe: Literal[False] = False) -> str: ...
@overload
def current_async_library(*, failsafe: Literal[True]) -> str | None: ...
def current_async_library(*, failsafe: bool = False) -> str | None:
    if (name := current_async_library_tlocal.name) is not None:
        return name

    if _curio_running():
        return "curio"

    if _asyncio_running():
        return "asyncio"

    if failsafe:
        return None

    msg = "unknown async library, or not in async context"
    raise AsyncLibraryNotFoundError(msg)
