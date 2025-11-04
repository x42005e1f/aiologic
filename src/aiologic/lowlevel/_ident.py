#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

from aiologic.meta import replaces

from ._greenlets import _current_greenlet
from ._libraries import current_async_library, current_green_library
from ._threads import _current_thread_or_main_greenlet, current_thread_ident


def _current_eventlet_token() -> object:
    global _current_eventlet_token

    from eventlet.hubs import get_hub as _current_eventlet_token

    return _current_eventlet_token()


def _current_gevent_token() -> object:
    global _current_gevent_token

    from gevent import get_hub as _current_gevent_token

    return _current_gevent_token()


def _current_asyncio_token() -> object:
    global _current_asyncio_token

    from asyncio import get_running_loop as _current_asyncio_token

    return _current_asyncio_token()


def _current_curio_token() -> object:
    from curio.meta import _locals

    @replaces(globals())
    def _current_curio_token():
        kernel = getattr(_locals, "kernel", None)

        if kernel is None:
            msg = "no running kernel"
            raise RuntimeError(msg)

        return kernel

    return _current_curio_token()


def _current_trio_token() -> object:
    global _current_trio_token

    from trio.lowlevel import current_trio_token as _current_trio_token

    return _current_trio_token()


def current_green_token() -> object:
    """..."""

    library = current_green_library()

    if library == "threading":
        return _current_thread_or_main_greenlet()

    if library == "eventlet":
        return _current_eventlet_token()

    if library == "gevent":
        return _current_gevent_token()

    msg = f"unsupported green library {library!r}"
    raise RuntimeError(msg)


def current_async_token() -> object:
    """..."""

    library = current_async_library()

    if library == "asyncio":
        return _current_asyncio_token()

    if library == "curio":
        return _current_curio_token()

    if library == "trio":
        return _current_trio_token()

    msg = f"unsupported async library {library!r}"
    raise RuntimeError(msg)


def current_green_token_ident() -> tuple[str, int]:
    """..."""

    library = current_green_library()

    if library == "threading":
        return (library, current_thread_ident())

    if library == "eventlet":
        return (library, id(_current_eventlet_token()))

    if library == "gevent":
        return (library, id(_current_gevent_token()))

    msg = f"unsupported green library {library!r}"
    raise RuntimeError(msg)


def current_async_token_ident() -> tuple[str, int]:
    """..."""

    library = current_async_library()

    if library == "asyncio":
        return (library, id(_current_asyncio_token()))

    if library == "curio":
        return (library, id(_current_curio_token()))

    if library == "trio":
        return (library, id(_current_trio_token()))

    msg = f"unsupported async library {library!r}"
    raise RuntimeError(msg)


def _current_asyncio_task() -> object:
    global _current_asyncio_task

    from asyncio import current_task as _current_asyncio_task

    return _current_asyncio_task()


def _current_curio_task() -> object:
    from functools import partial

    from curio.meta import _locals

    @replaces(globals())
    def _current_curio_task():
        try:
            cell = _locals._aiologic_task_cell
        except AttributeError:
            kernel = getattr(_locals, "kernel", None)

            if kernel is None:
                msg = "no running kernel"
                raise RuntimeError(msg) from None

            trap = kernel._traps["trap_get_current"]

            cell_index = trap.__code__.co_freevars.index("current")
            cell = trap.__closure__[cell_index]

            _locals._aiologic_task_cell = cell
            finalizer = partial(delattr, _locals, "_aiologic_task_cell")

            kernel._call_at_shutdown(finalizer)

        return cell.cell_contents

    return _current_curio_task()


def _current_trio_task() -> object:
    global _current_trio_task

    from trio.lowlevel import current_task as _current_trio_task

    return _current_trio_task()


def current_green_task() -> object:
    """..."""

    library = current_green_library()

    if library == "threading":
        return _current_thread_or_main_greenlet()

    if library == "eventlet":
        return _current_greenlet()

    if library == "gevent":
        return _current_greenlet()

    msg = f"unsupported green library {library!r}"
    raise RuntimeError(msg)


def current_async_task() -> object:
    """..."""

    library = current_async_library()

    if library == "asyncio":
        return _current_asyncio_task()

    if library == "curio":
        return _current_curio_task()

    if library == "trio":
        return _current_trio_task()

    msg = f"unsupported async library {library!r}"
    raise RuntimeError(msg)


def current_green_task_ident() -> tuple[str, int]:
    """..."""

    library = current_green_library()

    if library == "threading":
        return (library, current_thread_ident())

    if library == "eventlet":
        return (library, id(_current_greenlet()))

    if library == "gevent":
        return (library, id(_current_greenlet()))

    msg = f"unsupported green library {library!r}"
    raise RuntimeError(msg)


def current_async_task_ident() -> tuple[str, int]:
    """..."""

    library = current_async_library()

    if library == "asyncio":
        return (library, id(_current_asyncio_task()))

    if library == "curio":
        return (library, id(_current_curio_task()))

    if library == "trio":
        return (library, id(_current_trio_task()))

    msg = f"unsupported async library {library!r}"
    raise RuntimeError(msg)
