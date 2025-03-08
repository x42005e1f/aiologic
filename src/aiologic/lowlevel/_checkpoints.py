#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import os
import time

from contextvars import ContextVar
from inspect import isawaitable, iscoroutinefunction

from wrapt import decorator, when_imported

from ._libraries import current_async_library, current_green_library

threading_checkpoints_cvar = ContextVar(
    "threading_checkpoints_cvar",
    default=bool(os.getenv("AIOLOGIC_THREADING_CHECKPOINTS", "")),
)
eventlet_checkpoints_cvar = ContextVar(
    "eventlet_checkpoints_cvar",
    default=bool(os.getenv("AIOLOGIC_EVENTLET_CHECKPOINTS", "")),
)
gevent_checkpoints_cvar = ContextVar(
    "gevent_checkpoints_cvar",
    default=bool(os.getenv("AIOLOGIC_GEVENT_CHECKPOINTS", "")),
)

asyncio_checkpoints_cvar = ContextVar(
    "asyncio_checkpoints_cvar",
    default=bool(os.getenv("AIOLOGIC_ASYNCIO_CHECKPOINTS", "")),
)
curio_checkpoints_cvar = ContextVar(
    "curio_checkpoints_cvar",
    default=bool(os.getenv("AIOLOGIC_CURIO_CHECKPOINTS", "")),
)
trio_checkpoints_cvar = ContextVar(
    "trio_checkpoints_cvar",
    default=bool(os.getenv("AIOLOGIC_TRIO_CHECKPOINTS", "1")),
)


def _eventlet_checkpoint():
    global _eventlet_checkpoint

    from eventlet import sleep as _eventlet_checkpoint

    _eventlet_checkpoint()


def _gevent_checkpoint():
    global _gevent_checkpoint

    from gevent import sleep as _gevent_checkpoint

    _gevent_checkpoint()


def green_checkpoint(*, force=False):
    library = current_green_library(failsafe=True)

    if library == "threading":
        if force or threading_checkpoints_cvar.get():
            time.sleep(0)
    elif library == "eventlet":
        if force or eventlet_checkpoints_cvar.get():
            _eventlet_checkpoint()
    elif library == "gevent":
        if force or gevent_checkpoints_cvar.get():
            _gevent_checkpoint()


async def _asyncio_checkpoint():
    global _asyncio_checkpoint

    from asyncio import sleep

    async def _asyncio_checkpoint():
        await sleep(0)

    await _asyncio_checkpoint()


async def _curio_checkpoint():
    global _curio_checkpoint

    from curio import sleep

    async def _curio_checkpoint():
        await sleep(0)

    await _curio_checkpoint()


async def _trio_checkpoint():
    global _trio_checkpoint

    from trio.lowlevel import checkpoint as _trio_checkpoint

    await _trio_checkpoint()


async def checkpoint(*, force=False):
    library = current_async_library(failsafe=True)

    if library == "asyncio":
        if force or asyncio_checkpoints_cvar.get():
            await _asyncio_checkpoint()
    elif library == "curio":
        if force or curio_checkpoints_cvar.get():
            await _curio_checkpoint()
    elif library == "trio":
        if force or trio_checkpoints_cvar.get():
            await _trio_checkpoint()


async_checkpoint = checkpoint


async def _asyncio_checkpoint_if_cancelled():
    pass


@when_imported("anyio")
def _asyncio_checkpoint_if_cancelled_hook(_):
    global _asyncio_checkpoint_if_cancelled

    async def _asyncio_checkpoint_if_cancelled():
        global _asyncio_checkpoint_if_cancelled

        from anyio.lowlevel import checkpoint_if_cancelled

        _asyncio_checkpoint_if_cancelled = checkpoint_if_cancelled

        await _asyncio_checkpoint_if_cancelled()


async def _curio_checkpoint_if_cancelled():
    global _curio_checkpoint_if_cancelled

    from curio import check_cancellation as _curio_checkpoint_if_cancelled

    await _curio_checkpoint_if_cancelled()


async def _trio_checkpoint_if_cancelled():
    global _trio_checkpoint_if_cancelled

    from trio.lowlevel import checkpoint_if_cancelled

    _trio_checkpoint_if_cancelled = checkpoint_if_cancelled

    await _trio_checkpoint_if_cancelled()


async def checkpoint_if_cancelled(*, force=False):
    library = current_async_library(failsafe=True)

    if library == "asyncio":
        if force or asyncio_checkpoints_cvar.get():
            await _asyncio_checkpoint_if_cancelled()
    elif library == "curio":
        if force or curio_checkpoints_cvar.get():
            await _curio_checkpoint_if_cancelled()
    elif library == "trio":
        if force or trio_checkpoints_cvar.get():
            await _trio_checkpoint_if_cancelled()


def _eventlet_repeat_if_cancelled(wrapped, args, kwargs, /):
    global _eventlet_repeat_if_cancelled

    from eventlet import Timeout
    from eventlet.hubs import get_hub
    from greenlet import getcurrent

    def _eventlet_repeat_if_cancelled(wrapped, args, kwargs, /):
        timeouts = []

        try:
            while True:
                try:
                    result = wrapped(*args, **kwargs)
                except Timeout as timeout:
                    timeouts.append(timeout)
                else:
                    break

            if timeouts:
                raise timeouts[0]
        finally:
            try:
                for timeout in timeouts[1:]:
                    if not timeout.pending:
                        timeout.timer = get_hub().schedule_call_global(
                            0,
                            getcurrent().throw,
                            timeout,
                        )
            finally:
                del timeouts

        return result

    return _eventlet_repeat_if_cancelled(wrapped, args, kwargs)


def _gevent_repeat_if_cancelled(wrapped, args, kwargs, /):
    global _gevent_repeat_if_cancelled

    from gevent import Timeout, get_hub
    from greenlet import getcurrent

    def _gevent_repeat_if_cancelled(wrapped, args, kwargs, /):
        timeouts = []

        try:
            while True:
                try:
                    result = wrapped(*args, **kwargs)
                except Timeout as timeout:
                    timeouts.append(timeout)
                else:
                    break

            if timeouts:
                raise timeouts[0]
        finally:
            try:
                for timeout in timeouts[:0:-1]:
                    if not timeout.pending:
                        timeout.timer.close()
                        timeout.timer = get_hub().loop.run_callback(
                            getcurrent().throw,
                            timeout,
                        )
            finally:
                del timeouts

        return result

    return _gevent_repeat_if_cancelled(wrapped, args, kwargs)


@decorator
def _green_repeat_if_cancelled(wrapped, instance, args, kwargs, /):
    library = current_green_library()

    if library == "threading":
        result = wrapped(*args, **kwargs)
    elif library == "eventlet":
        result = _eventlet_repeat_if_cancelled(wrapped, args, kwargs)
    elif library == "gevent":
        result = _gevent_repeat_if_cancelled(wrapped, args, kwargs)
    else:
        msg = f"unsupported green library {library!r}"
        raise RuntimeError(msg)

    return result


async def _asyncio_repeat_if_cancelled(wrapped, args, kwargs, /):
    global _asyncio_repeat_if_cancelled

    from asyncio import CancelledError

    async def _asyncio_repeat_if_cancelled(wrapped, args, kwargs, /):
        exc = None

        try:
            while True:
                try:
                    if args is None:
                        result = await wrapped
                    else:
                        result = await wrapped(*args, **kwargs)
                except CancelledError as e:
                    exc = e
                else:
                    break

            if exc is not None:
                raise exc
        finally:
            del exc

        return result

    return await _asyncio_repeat_if_cancelled(wrapped, args, kwargs)


@when_imported("anyio")
def _asyncio_repeat_if_cancelled_hook(_):
    global _asyncio_repeat_if_cancelled

    async def _asyncio_repeat_if_cancelled(wrapped, args, kwargs, /):
        global _asyncio_repeat_if_cancelled

        from asyncio import CancelledError

        from anyio import CancelScope

        async def _asyncio_repeat_if_cancelled(wrapped, args, kwargs, /):
            with CancelScope(shield=True):
                exc = None

                try:
                    while True:
                        try:
                            if args is None:
                                result = await wrapped
                            else:
                                result = await wrapped(*args, **kwargs)
                        except CancelledError as e:
                            exc = e
                        else:
                            break

                    if exc is not None:
                        raise exc
                finally:
                    del exc

            return result

        return await _asyncio_repeat_if_cancelled(wrapped, args, kwargs)


async def _curio_repeat_if_cancelled(wrapped, args, kwargs, /):
    global _curio_repeat_if_cancelled

    from curio import disable_cancellation

    async def _curio_repeat_if_cancelled(wrapped, args, kwargs, /):
        async with disable_cancellation():
            if args is None:
                return await wrapped
            else:
                return await wrapped(*args, **kwargs)

    return await _curio_repeat_if_cancelled(wrapped, args, kwargs)


async def _trio_repeat_if_cancelled(wrapped, args, kwargs, /):
    global _trio_repeat_if_cancelled

    from trio import CancelScope

    async def _trio_repeat_if_cancelled(wrapped, args, kwargs, /):
        with CancelScope(shield=True):
            if args is None:
                return await wrapped
            else:
                return await wrapped(*args, **kwargs)

    return await _trio_repeat_if_cancelled(wrapped, args, kwargs)


@decorator
async def _async_repeat_if_cancelled(wrapped, instance, args, kwargs, /):
    library = current_async_library()

    if library == "asyncio":
        result = await _asyncio_repeat_if_cancelled(wrapped, args, kwargs)
    elif library == "curio":
        result = await _curio_repeat_if_cancelled(wrapped, args, kwargs)
    elif library == "trio":
        result = await _trio_repeat_if_cancelled(wrapped, args, kwargs)
    else:
        msg = f"unsupported async library {library!r}"
        raise RuntimeError(msg)

    return result


async def _async_repeat_if_cancelled_for_awaitable(wrapped, /):
    library = current_async_library()

    if library == "asyncio":
        result = await _asyncio_repeat_if_cancelled(wrapped, None, None)
    elif library == "curio":
        result = await _curio_repeat_if_cancelled(wrapped, None, None)
    elif library == "trio":
        result = await _trio_repeat_if_cancelled(wrapped, None, None)
    else:
        msg = f"unsupported async library {library!r}"
        raise RuntimeError(msg)

    return result


def repeat_if_cancelled(wrapped, /):
    if isawaitable(wrapped):
        return _async_repeat_if_cancelled_for_awaitable(wrapped)
    elif iscoroutinefunction(wrapped):
        return _async_repeat_if_cancelled(wrapped)
    else:
        return _green_repeat_if_cancelled(wrapped)


async def _asyncio_cancel_shielded_checkpoint():
    global _asyncio_cancel_shielded_checkpoint

    from asyncio import shield, sleep

    async def _asyncio_cancel_shielded_checkpoint():
        await shield(sleep(0))

    await _asyncio_cancel_shielded_checkpoint()


@when_imported("anyio")
def _asyncio_cancel_shielded_checkpoint_hook(_):
    global _asyncio_cancel_shielded_checkpoint

    async def _asyncio_cancel_shielded_checkpoint():
        global _asyncio_cancel_shielded_checkpoint

        from anyio.lowlevel import cancel_shielded_checkpoint

        _asyncio_cancel_shielded_checkpoint = cancel_shielded_checkpoint

        await _asyncio_cancel_shielded_checkpoint()


async def _curio_cancel_shielded_checkpoint():
    global _curio_cancel_shielded_checkpoint

    from curio import disable_cancellation, sleep

    async def _curio_cancel_shielded_checkpoint():
        async with disable_cancellation():
            await sleep(0)

    await _curio_cancel_shielded_checkpoint()


async def _trio_cancel_shielded_checkpoint():
    global _trio_cancel_shielded_checkpoint

    from trio.lowlevel import cancel_shielded_checkpoint

    _trio_cancel_shielded_checkpoint = cancel_shielded_checkpoint

    await _trio_cancel_shielded_checkpoint()


async def cancel_shielded_checkpoint(*, force=False):
    library = current_async_library(failsafe=True)

    if library == "asyncio":
        if force or asyncio_checkpoints_cvar.get():
            await _asyncio_cancel_shielded_checkpoint()
    elif library == "curio":
        if force or curio_checkpoints_cvar.get():
            await _curio_cancel_shielded_checkpoint()
    elif library == "trio":
        if force or trio_checkpoints_cvar.get():
            await _trio_cancel_shielded_checkpoint()
