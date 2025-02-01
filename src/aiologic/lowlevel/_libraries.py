#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import os

from sys import modules

from ._threads import ThreadLocal

DEFAULT_GREEN_LIBRARY = os.getenv("AIOLOGIC_GREEN_LIBRARY") or None
DEFAULT_ASYNC_LIBRARY = os.getenv("AIOLOGIC_ASYNC_LIBRARY") or None


class GreenLibraryNotFoundError(RuntimeError):
    pass


class NamedLocal(ThreadLocal):
    name = None


current_green_library_tlocal = NamedLocal()


def _threading_running_impl():
    return True


def _eventlet_running_impl():
    global _eventlet_running_impl

    if "eventlet" in modules:
        from eventlet.hubs import _threadlocal

        def _eventlet_running_impl():
            return getattr(_threadlocal, "hub", None) is not None

        answer = _eventlet_running_impl()
    else:
        answer = False

    return answer


def _gevent_running_impl():
    global _gevent_running_impl

    if "gevent" in modules:
        from gevent._hub_local import get_hub_if_exists

        def _gevent_running_impl():
            return get_hub_if_exists() is not None

        answer = _gevent_running_impl()
    else:
        answer = False

    return answer


def threading_running():
    if (name := current_green_library_tlocal.name) is not None:
        running = name == "threading"
    elif (name := DEFAULT_GREEN_LIBRARY) is not None:
        running = name == "threading"
    else:
        running = _threading_running_impl()

    return running


def eventlet_running():
    if (name := current_green_library_tlocal.name) is not None:
        running = name == "eventlet"
    elif (name := DEFAULT_GREEN_LIBRARY) is not None:
        running = name == "eventlet"
    else:
        running = _eventlet_running_impl()

    return running


def gevent_running():
    if (name := current_green_library_tlocal.name) is not None:
        running = name == "gevent"
    elif (name := DEFAULT_GREEN_LIBRARY) is not None:
        running = name == "gevent"
    else:
        running = _gevent_running_impl()

    return running


def current_green_library(*, failsafe=False):
    if (name := current_green_library_tlocal.name) is not None:
        library = name
    elif (name := DEFAULT_GREEN_LIBRARY) is not None:
        library = name
    elif _gevent_running_impl():
        library = "gevent"
    elif _eventlet_running_impl():
        library = "eventlet"
    elif _threading_running_impl():
        library = "threading"
    elif failsafe:
        library = None
    else:
        msg = "unknown green library, or not in green context"
        raise GreenLibraryNotFoundError(msg)

    return library


try:
    from sniffio import (
        AsyncLibraryNotFoundError,
        thread_local as current_async_library_tlocal,
    )
except ImportError:

    class AsyncLibraryNotFoundError(RuntimeError):
        pass

    current_async_library_tlocal = NamedLocal()


def _asyncio_running_impl():
    global _asyncio_running_impl

    if "asyncio" in modules:
        try:
            from asyncio import _get_running_loop as get_running_loop
        except ImportError:
            from asyncio import get_running_loop

        def _asyncio_running_impl():
            try:
                running = get_running_loop() is not None
            except RuntimeError:
                running = False

            return running

        running = _asyncio_running_impl()
    else:
        running = False

    return running


def _curio_running_impl():
    global _curio_running_impl

    if "curio" in modules:
        from curio.meta import curio_running

        _curio_running_impl = curio_running

        running = _curio_running_impl()
    else:
        running = False

    return running


def asyncio_running():
    if (name := current_async_library_tlocal.name) is not None:
        running = name == "asyncio"
    elif (name := DEFAULT_ASYNC_LIBRARY) is not None:
        running = name == "asyncio"
    else:
        running = _asyncio_running_impl()

    return running


def curio_running():
    if (name := current_async_library_tlocal.name) is not None:
        running = name == "curio"
    elif (name := DEFAULT_ASYNC_LIBRARY) is not None:
        running = name == "curio"
    else:
        running = _curio_running_impl()

    return running


def trio_running():
    if (name := current_async_library_tlocal.name) is not None:
        running = name == "trio"
    elif (name := DEFAULT_ASYNC_LIBRARY) is not None:
        running = name == "trio"
    else:
        running = False

    return running


def current_async_library(*, failsafe=False):
    if (name := current_async_library_tlocal.name) is not None:
        library = name
    elif (name := DEFAULT_ASYNC_LIBRARY) is not None:
        library = name
    elif _asyncio_running_impl():
        library = "asyncio"
    elif _curio_running_impl():
        library = "curio"
    elif failsafe:
        library = None
    else:
        msg = "unknown async library, or not in async context"
        raise AsyncLibraryNotFoundError(msg)

    return library
