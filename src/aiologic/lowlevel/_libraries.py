#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from typing import TYPE_CHECKING, Literal

from sniffio import (
    AsyncLibraryNotFoundError as AsyncLibraryNotFoundError,
    thread_local,
)
from wrapt import when_imported

from aiologic.meta import replaces

from ._safety import signal_safety_enabled
from ._threads import _local

if sys.version_info >= (3, 11):
    from typing import overload
else:
    from typing_extensions import overload

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
    @replaces(globals())
    def _eventlet_running():
        # eventlet does not provide a public function to get the current hub
        # without creating a new one when there is none, so we use its private
        # API.

        from eventlet.hubs import _threadlocal

        @replaces(globals())
        def _eventlet_running():
            return getattr(_threadlocal, "hub", None) is not None

        return _eventlet_running()


@when_imported("gevent")
def _(_):
    @replaces(globals())
    def _gevent_running():
        # gevent does not provide a public function to get the current hub
        # without creating a new one when there is none, so we use its private
        # API.

        from gevent._hub_local import get_hub_if_exists

        @replaces(globals())
        def _gevent_running():
            return get_hub_if_exists() is not None

        return _gevent_running()


@when_imported("asyncio")
def _(_):
    @replaces(globals())
    def _asyncio_running():
        # While asyncio.get_running_loop() will work to get the current event
        # loop, it will also raise a RuntimeError if there is none, which can
        # be relatively slow to handle on CPython. So instead we use
        # asyncio._get_running_loop(), which returns None in that case.

        from asyncio import _get_running_loop
        from sys import version_info

        is_builtin = _get_running_loop.__module__ == "_asyncio"

        # Since Python 3.12, the built-in (C-level) asyncio._get_running_loop()
        # bypasses the slow os.getpid() call and thus runs fast, so we rely on
        # it in this case. But in the other case, we try
        # sniffio.current_async_library_cvar.get() before
        # asyncio._get_running_loop() to improve performance at least for calls
        # in an active anyio run.

        if version_info >= (3, 12) and is_builtin:

            @replaces(globals())
            def _asyncio_running():
                return _get_running_loop() is not None

        else:
            from sniffio import current_async_library_cvar

            @replaces(globals())
            def _asyncio_running():
                return (
                    current_async_library_cvar.get() == "asyncio"
                    or _get_running_loop() is not None
                )

        return _asyncio_running()


@when_imported("curio")
def _(_):
    @replaces(globals())
    def _curio_running():
        global _curio_running

        from curio.meta import curio_running as _curio_running

        return _curio_running()


@overload
def current_green_library(*, failsafe: Literal[False] = False) -> str: ...
@overload
def current_green_library(*, failsafe: Literal[True]) -> str | None: ...
def current_green_library(*, failsafe=False):
    """
    Detect which green library is currently running.

    Args:
      failsafe:
        Unless set to :data:`True`, the function will raise an exception when
        there is no current green library. Otherwise the function returns
        :type:`None` in that case.

    Returns:
      A string like ``"gevent"`` or :data:`None`.

    Raises:
      GreenLibraryNotFoundError:
        if the current green library was not recognized.

    Example:
      .. code:: python

        def green_sleep(seconds: float) -> None:
            match library := aiologic.lowlevel.current_green_library():
                case "threading":
                    time.sleep(seconds)
                case "eventlet":
                    eventlet.sleep(seconds)
                case "gevent":
                    gevent.sleep(seconds)
                case _:
                    msg = f"unsupported green library {library!r}"
                    raise RuntimeError(msg)
    """

    if not signal_safety_enabled():
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
def current_async_library(*, failsafe=False):
    """
    Detect which async library is currently running.

    Args:
      failsafe:
        Unless set to :data:`True`, the function will raise an exception when
        there is no current async library. Otherwise the function returns
        :type:`None` in that case.

    Returns:
      A string like ``"trio"`` or :data:`None`.

    Raises:
      AsyncLibraryNotFoundError:
        if the current async library was not recognized.

    Example:
      .. code:: python

        async def async_sleep(seconds: float) -> None:
            match library := aiologic.lowlevel.current_async_library():
                case "asyncio":
                    await asyncio.sleep(seconds)
                case "curio":
                    await curio.sleep(seconds)
                case "trio":
                    await trio.sleep(seconds)
                case _:
                    msg = f"unsupported async library {library!r}"
                    raise RuntimeError(msg)
    """

    if not signal_safety_enabled():
        if (name := current_async_library_tlocal.name) is not None:
            return name

        # trio is detected via current_async_library_tlocal.name

        if _curio_running():
            return "curio"

        if _asyncio_running():
            return "asyncio"

    if failsafe:
        return None

    msg = "unknown async library, or not in async context"
    raise AsyncLibraryNotFoundError(msg)
