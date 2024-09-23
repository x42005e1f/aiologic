#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

__all__ = (
    "GreenLibraryNotFoundError",
    "AsyncLibraryNotFoundError",
    "current_green_library_tlocal",
    "current_async_library_tlocal",
    "current_async_library_cvar",
    "current_green_library",
    "current_async_library",
    "threading_running",
    "eventlet_running",
    "gevent_running",
    "asyncio_running",
    "curio_running",
    "trio_running",
)

import os

from sys import modules

from . import patcher
from .threads import ThreadLocal

GREEN_LIBRARY_DEFAULT = os.getenv("AIOLOGIC_GREEN_LIBRARY") or None
ASYNC_LIBRARY_DEFAULT = os.getenv("AIOLOGIC_ASYNC_LIBRARY") or None


class GreenLibraryNotFoundError(RuntimeError):
    pass


class NamedLocal(ThreadLocal):
    name = None


current_green_library_tlocal = NamedLocal()


def threading_running_impl():
    global threading_running_impl

    try:
        from .thread import get_ident  # noqa: F401
    except ImportError:

        def threading_running_impl():
            return False

    else:

        def threading_running_impl():
            return True

    return threading_running_impl()


def eventlet_running_impl():
    global eventlet_running_impl

    if patcher.eventlet_patched("threading"):

        def eventlet_running_impl():
            return True

    else:

        def eventlet_running_impl():
            return False

    return eventlet_running_impl()


def gevent_running_impl():
    global gevent_running_impl

    if patcher.gevent_patched("threading"):

        def gevent_running_impl():
            return True

    else:

        def gevent_running_impl():
            return False

    return gevent_running_impl()


def threading_running():
    if (name := current_green_library_tlocal.name) is not None:
        running = name == "threading"
    elif (name := GREEN_LIBRARY_DEFAULT) is not None:
        running = name == "threading"
    else:
        running = threading_running_impl()

    return running


def eventlet_running():
    if (name := current_green_library_tlocal.name) is not None:
        running = name == "eventlet"
    elif (name := GREEN_LIBRARY_DEFAULT) is not None:
        running = name == "eventlet"
    else:
        running = eventlet_running_impl()

    return running


def gevent_running():
    if (name := current_green_library_tlocal.name) is not None:
        running = name == "gevent"
    elif (name := GREEN_LIBRARY_DEFAULT) is not None:
        running = name == "gevent"
    else:
        running = gevent_running_impl()

    return running


def current_green_library(*, failsafe=False):
    if (name := current_green_library_tlocal.name) is not None:
        library = name
    elif (name := GREEN_LIBRARY_DEFAULT) is not None:
        library = name
    elif eventlet_running_impl():
        library = "eventlet"
    elif gevent_running_impl():
        library = "gevent"
    elif threading_running_impl():
        library = "threading"
    elif failsafe:
        library = None
    else:
        raise GreenLibraryNotFoundError(
            "unknown green library, or not in green context",
        )

    return library


try:
    from sniffio import (
        AsyncLibraryNotFoundError,
        thread_local as current_async_library_tlocal,
        current_async_library_cvar,
    )
except ImportError:
    from contextvars import ContextVar

    class AsyncLibraryNotFoundError(RuntimeError):
        pass

    current_async_library_tlocal = NamedLocal()
    current_async_library_cvar = ContextVar(
        "current_async_library_cvar",
        default=None,
    )


def asyncio_running_impl():
    global asyncio_running_impl

    if "asyncio" in modules:
        try:
            from asyncio import current_task as current_asyncio_task
        except ImportError:

            def asyncio_running_impl():
                return False

        else:

            def asyncio_running_impl():
                try:
                    running = current_asyncio_task() is not None
                except RuntimeError:
                    running = False

                return running

        running = asyncio_running_impl()
    else:
        running = False

    return running


def curio_running_impl():
    global curio_running_impl

    if "curio" in modules:
        try:
            from curio.meta import curio_running as curio_running_impl
        except ImportError:

            def curio_running_impl():
                return False

        running = curio_running_impl()
    else:
        running = False

    return running


def asyncio_running():
    if (name := current_async_library_tlocal.name) is not None:
        running = name == "asyncio"
    elif (name := current_async_library_cvar.get()) is not None:
        running = name == "asyncio"
    elif (name := ASYNC_LIBRARY_DEFAULT) is not None:
        running = name == "asyncio"
    else:
        running = asyncio_running_impl()

    return running


def curio_running():
    if (name := current_async_library_tlocal.name) is not None:
        running = name == "curio"
    elif (name := current_async_library_cvar.get()) is not None:
        running = name == "curio"
    elif (name := ASYNC_LIBRARY_DEFAULT) is not None:
        running = name == "curio"
    else:
        running = curio_running_impl()

    return running


def trio_running():
    if (name := current_async_library_tlocal.name) is not None:
        running = name == "trio"
    elif (name := current_async_library_cvar.get()) is not None:
        running = name == "trio"
    elif (name := ASYNC_LIBRARY_DEFAULT) is not None:
        running = name == "trio"
    else:
        running = False

    return running


def current_async_library(*, failsafe=False):
    if (name := current_async_library_tlocal.name) is not None:
        library = name
    elif (name := current_async_library_cvar.get()) is not None:
        library = name
    elif (name := ASYNC_LIBRARY_DEFAULT) is not None:
        library = name
    elif asyncio_running_impl():
        library = "asyncio"
    elif curio_running_impl():
        library = "curio"
    elif failsafe:
        library = None
    else:
        raise AsyncLibraryNotFoundError(
            "unknown async library, or not in async context",
        )

    return library
