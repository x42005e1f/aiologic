#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import os

from wrapt import when_imported

from ._threads import ThreadLocal

DEFAULT_GREEN_LIBRARY = os.getenv("AIOLOGIC_GREEN_LIBRARY") or None
DEFAULT_ASYNC_LIBRARY = os.getenv("AIOLOGIC_ASYNC_LIBRARY") or None


class GreenLibraryNotFoundError(RuntimeError):
    pass


class _NamedLocal(ThreadLocal):
    name = None


current_green_library_tlocal = _NamedLocal()


def _get_gevent_hub_if_exists():
    return None


@when_imported("gevent")
def _get_gevent_hub_if_exists_hook(_):
    global _get_gevent_hub_if_exists

    def _get_gevent_hub_if_exists():
        global _get_gevent_hub_if_exists

        from gevent._hub_local import get_hub_if_exists

        _get_gevent_hub_if_exists = get_hub_if_exists

        return _get_gevent_hub_if_exists()


def gevent_running():
    if (name := current_green_library_tlocal.name) is not None:
        running = name == "gevent"
    elif (name := DEFAULT_GREEN_LIBRARY) is not None:
        running = name == "gevent"
    else:
        running = _get_gevent_hub_if_exists() is not None

    return running


def _get_eventlet_hub_if_exists():
    return None


@when_imported("eventlet")
def _get_eventlet_hub_if_exists_hook(_):
    global _get_eventlet_hub_if_exists

    def _get_eventlet_hub_if_exists():
        global _get_eventlet_hub_if_exists

        from eventlet.hubs import _threadlocal

        def _get_eventlet_hub_if_exists():
            return getattr(_threadlocal, "hub", None)

        return _get_eventlet_hub_if_exists()


def eventlet_running():
    if (name := current_green_library_tlocal.name) is not None:
        running = name == "eventlet"
    elif (name := DEFAULT_GREEN_LIBRARY) is not None:
        running = name == "eventlet"
    elif _get_gevent_hub_if_exists() is not None:
        running = False
    else:
        running = _get_eventlet_hub_if_exists() is not None

    return running


def threading_running():
    if (name := current_green_library_tlocal.name) is not None:
        running = name == "threading"
    elif (name := DEFAULT_GREEN_LIBRARY) is not None:
        running = name == "threading"
    elif _get_gevent_hub_if_exists() is not None:
        running = False
    elif _get_eventlet_hub_if_exists() is not None:
        running = False
    else:
        running = True

    return running


def current_green_library(*, failsafe=False):
    if (name := current_green_library_tlocal.name) is not None:
        library = name
    elif (name := DEFAULT_GREEN_LIBRARY) is not None:
        library = name
    elif _get_gevent_hub_if_exists() is not None:
        library = "gevent"
    elif _get_eventlet_hub_if_exists() is not None:
        library = "eventlet"
    else:
        library = "threading"

    return library


try:
    from sniffio import (
        AsyncLibraryNotFoundError,
        thread_local as current_async_library_tlocal,
    )
except ImportError:

    class AsyncLibraryNotFoundError(RuntimeError):
        pass

    current_async_library_tlocal = _NamedLocal()


def trio_running():
    if (name := current_async_library_tlocal.name) is not None:
        running = name == "trio"
    elif (name := DEFAULT_ASYNC_LIBRARY) is not None:
        running = name == "trio"
    else:
        running = False

    return running


def _curio_running():
    return False


@when_imported("curio")
def _curio_running_hook(_):
    global _curio_running

    def _curio_running():
        global _curio_running

        from curio.meta import curio_running as _curio_running

        return _curio_running()


def curio_running():
    if (name := current_async_library_tlocal.name) is not None:
        running = name == "curio"
    elif (name := DEFAULT_ASYNC_LIBRARY) is not None:
        running = name == "curio"
    else:
        running = _curio_running()

    return running


def _get_asyncio_marker_if_exists():
    return None


@when_imported("asyncio")
def _get_asyncio_marker_if_exists_hook(_):
    global _get_asyncio_marker_if_exists

    def _get_asyncio_marker_if_exists():
        global _get_asyncio_marker_if_exists

        from asyncio import _get_running_loop
        from sys import version_info

        is_builtin = _get_running_loop.__module__ == "_asyncio"

        _get_asyncio_marker_if_exists = _get_running_loop

        if version_info < (3, 12) or not is_builtin:

            @when_imported("sniffio")
            def _get_asyncio_marker_if_exists_hook(_):
                global _get_asyncio_marker_if_exists

                def _get_asyncio_marker_if_exists():
                    global _get_asyncio_marker_if_exists

                    from sniffio import current_async_library_cvar as cvar

                    def _get_asyncio_marker_if_exists():
                        if (name := cvar.get()) is not None:
                            return (name == "asyncio") or None
                        else:
                            return _get_running_loop()

                    return _get_asyncio_marker_if_exists()

        return _get_asyncio_marker_if_exists()


def asyncio_running():
    if (name := current_async_library_tlocal.name) is not None:
        running = name == "asyncio"
    elif (name := DEFAULT_ASYNC_LIBRARY) is not None:
        running = name == "asyncio"
    elif _curio_running():
        running = False
    else:
        running = _get_asyncio_marker_if_exists() is not None

    return running


def current_async_library(*, failsafe=False):
    if (name := current_async_library_tlocal.name) is not None:
        library = name
    elif (name := DEFAULT_ASYNC_LIBRARY) is not None:
        library = name
    elif _curio_running():
        library = "curio"
    elif _get_asyncio_marker_if_exists() is not None:
        library = "asyncio"
    elif failsafe:
        library = None
    else:
        msg = "unknown async library, or not in async context"
        raise AsyncLibraryNotFoundError(msg)

    return library
