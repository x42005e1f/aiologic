#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

__all__ = (
    "current_async_task",
    "current_async_task_ident",
    "current_async_token",
    "current_async_token_ident",
    "current_green_task",
    "current_green_task_ident",
    "current_green_token",
    "current_green_token_ident",
    "current_thread",
    "current_thread_ident",
)

from .libraries import current_async_library, current_green_library
from .threads import current_thread

try:
    from .thread import get_ident as current_thread_ident
except ImportError:

    def current_thread_ident():
        raise NotImplementedError


def current_eventlet_token():  # noqa: F811
    global current_eventlet_token

    try:
        from eventlet.hubs import get_hub as current_eventlet_token
    except ImportError:

        def current_eventlet_token():
            raise NotImplementedError

    return current_eventlet_token()


def current_gevent_token():  # noqa: F811
    global current_gevent_token

    try:
        from gevent import get_hub as current_gevent_token
    except ImportError:

        def current_gevent_token():
            raise NotImplementedError

    return current_gevent_token()


def current_green_token():
    library = current_green_library()

    if library == "threading":
        token = None
    elif library == "eventlet":
        token = current_eventlet_token()
    elif library == "gevent":
        token = current_gevent_token()
    else:
        msg = f"unsupported green library {library!r}"
        raise RuntimeError(msg)

    return token


def current_green_token_ident():
    library = current_green_library()

    if library == "threading":
        ident = (library, 1)
    elif library == "eventlet":
        ident = (library, id(current_eventlet_token()))
    elif library == "gevent":
        ident = (library, id(current_gevent_token()))
    else:
        msg = f"unsupported green library {library!r}"
        raise RuntimeError(msg)

    return ident


def current_asyncio_token():  # noqa: F811
    global current_asyncio_token

    try:
        from asyncio import get_running_loop as current_asyncio_token
    except ImportError:

        def current_asyncio_token():
            raise NotImplementedError

    return current_asyncio_token()


def current_trio_token():  # noqa: F811
    global current_trio_token

    try:
        from trio.lowlevel import current_trio_token
    except ImportError:

        def current_trio_token():
            raise NotImplementedError

    return current_trio_token()


def current_async_token():
    library = current_async_library()

    if library == "asyncio":
        token = current_asyncio_token()
    elif library == "trio":
        token = current_trio_token()
    else:
        msg = f"unsupported async library {library!r}"
        raise RuntimeError(msg)

    return token


def current_async_token_ident():
    library = current_async_library()

    if library == "asyncio":
        ident = (library, id(current_asyncio_token()))
    elif library == "trio":
        ident = (library, id(current_trio_token()))
    else:
        msg = f"unsupported async library {library!r}"
        raise RuntimeError(msg)

    return ident


def current_greenlet():  # noqa: F811
    global current_greenlet

    try:
        from greenlet import getcurrent as current_greenlet
    except ImportError:

        def current_greenlet():
            raise NotImplementedError

    return current_greenlet()


def current_green_task():
    library = current_green_library()

    if library == "threading":
        task = current_thread()
    elif library == "eventlet":
        task = current_greenlet()
    elif library == "gevent":
        task = current_greenlet()
    else:
        msg = f"unsupported green library {library!r}"
        raise RuntimeError(msg)

    return task


def current_green_task_ident():
    library = current_green_library()

    if library == "threading":
        ident = (library, current_thread_ident())
    elif library == "eventlet":
        ident = (library, id(current_greenlet()))
    elif library == "gevent":
        ident = (library, id(current_greenlet()))
    else:
        msg = f"unsupported green library {library!r}"
        raise RuntimeError(msg)

    return ident


def current_asyncio_task():  # noqa: F811
    global current_asyncio_task

    try:
        from asyncio import current_task as current_asyncio_task
    except ImportError:

        def current_asyncio_task():
            raise NotImplementedError

    return current_asyncio_task()


def current_trio_task():  # noqa: F811
    global current_trio_task

    try:
        from trio.lowlevel import current_task as current_trio_task
    except ImportError:

        def current_trio_task():
            raise NotImplementedError

    return current_trio_task()


def current_async_task():
    library = current_async_library()

    if library == "asyncio":
        task = current_asyncio_task()
    elif library == "trio":
        task = current_trio_task()
    else:
        msg = f"unsupported async library {library!r}"
        raise RuntimeError(msg)

    return task


def current_async_task_ident():
    library = current_async_library()

    if library == "asyncio":
        ident = (library, id(current_asyncio_task()))
    elif library == "trio":
        ident = (library, id(current_trio_task()))
    else:
        msg = f"unsupported async library {library!r}"
        raise RuntimeError(msg)

    return ident
