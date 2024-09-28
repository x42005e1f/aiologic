#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

__all__ = (
    "shield",
    "checkpoint",
    "green_checkpoint",
    "checkpoint_if_cancelled",
    "cancel_shielded_checkpoint",
    "threading_checkpoints_cvar",
    "eventlet_checkpoints_cvar",
    "gevent_checkpoints_cvar",
    "asyncio_checkpoints_cvar",
    "curio_checkpoints_cvar",
    "trio_checkpoints_cvar",
)

import os
import time
import platform

from functools import partial
from contextvars import ContextVar

from .libraries import (
    AsyncLibraryNotFoundError,
    current_async_library,
    current_green_library,
)

PYTHON_IMPLEMENTATION = platform.python_implementation()

threading_checkpoints_cvar = ContextVar(
    "threading_checkpoints_cvar",
    default=(bool(os.getenv("AIOLOGIC_THREADING_CHECKPOINTS", ""))),
)
eventlet_checkpoints_cvar = ContextVar(
    "eventlet_checkpoints_cvar",
    default=(bool(os.getenv("AIOLOGIC_EVENTLET_CHECKPOINTS", ""))),
)
gevent_checkpoints_cvar = ContextVar(
    "gevent_checkpoints_cvar",
    default=(bool(os.getenv("AIOLOGIC_GEVENT_CHECKPOINTS", ""))),
)

asyncio_checkpoints_cvar = ContextVar(
    "asyncio_checkpoints_cvar",
    default=(bool(os.getenv("AIOLOGIC_ASYNCIO_CHECKPOINTS", ""))),
)
curio_checkpoints_cvar = ContextVar(
    "curio_checkpoints_cvar",
    default=(bool(os.getenv("AIOLOGIC_CURIO_CHECKPOINTS", ""))),
)
trio_checkpoints_cvar = ContextVar(
    "trio_checkpoints_cvar",
    default=(bool(os.getenv("AIOLOGIC_TRIO_CHECKPOINTS", "1"))),
)


def eventlet_checkpoint():
    global eventlet_checkpoint

    try:
        from eventlet import sleep as eventlet_checkpoint
    except ImportError:

        def eventlet_checkpoint():
            pass

    eventlet_checkpoint()


def gevent_checkpoint():
    global gevent_checkpoint

    try:
        from gevent import sleep as gevent_checkpoint
    except ImportError:

        def gevent_checkpoint():
            pass

    gevent_checkpoint()


def green_checkpoint(*, force=False):
    library = current_green_library(failsafe=True)

    if library == "threading":
        if force or threading_checkpoints_cvar.get():
            time.sleep(0)
    elif library == "eventlet":
        if force or eventlet_checkpoints_cvar.get():
            eventlet_checkpoint()
    elif library == "gevent":
        if force or gevent_checkpoints_cvar.get():
            gevent_checkpoint()


async def asyncio_shield(coro):
    global asyncio_shield

    try:
        from anyio import CancelScope
    except ImportError:
        try:
            from asyncio import shield as asyncio_shield
        except ImportError:

            async def asyncio_shield(coro):
                raise NotImplementedError

    else:

        async def asyncio_shield(coro):
            with CancelScope(shield=True):
                return await coro

    return await asyncio_shield(coro)


async def curio_shield(coro):
    global curio_shield

    try:
        from curio import disable_cancellation as curio_disable_cancellation
    except ImportError:

        async def curio_shield(coro):
            raise NotImplementedError

    else:

        async def curio_shield(coro):
            async with curio_disable_cancellation():
                return await coro

    return await curio_shield(coro)


async def trio_shield(coro):
    global trio_shield

    try:
        from anyio import CancelScope
    except ImportError:
        try:
            from trio import CancelScope
        except ImportError:

            async def trio_shield(coro):
                raise NotImplementedError

        else:

            async def trio_shield(coro):
                with CancelScope(shield=True):
                    return await coro

    else:

        async def trio_shield(coro):
            with CancelScope(shield=True):
                return await coro

    return await trio_shield(coro)


async def asyncio_checkpoint():
    global asyncio_checkpoint

    try:
        from anyio.lowlevel import checkpoint as asyncio_checkpoint
    except ImportError:
        try:
            from asyncio import sleep as asyncio_sleep
        except ImportError:

            async def asyncio_checkpoint():
                pass

        else:
            asyncio_checkpoint = partial(asyncio_sleep, 0)

    await asyncio_checkpoint()


async def curio_checkpoint():
    global curio_checkpoint

    try:
        from curio import sleep as curio_sleep
    except ImportError:

        async def curio_checkpoint():
            pass

    else:
        curio_checkpoint = partial(curio_sleep, 0)

    await curio_checkpoint()


async def trio_checkpoint():
    global trio_checkpoint

    try:
        from anyio.lowlevel import checkpoint as trio_checkpoint
    except ImportError:
        try:
            from trio.lowlevel import checkpoint as trio_checkpoint
        except ImportError:

            async def trio_checkpoint():
                pass

    await trio_checkpoint()


async def asyncio_checkpoint_if_cancelled():
    global asyncio_checkpoint_if_cancelled

    try:
        from anyio.lowlevel import (
            checkpoint_if_cancelled as asyncio_checkpoint_if_cancelled,
        )
    except ImportError:

        async def asyncio_checkpoint_if_cancelled():
            pass

    await asyncio_checkpoint_if_cancelled()


async def curio_checkpoint_if_cancelled():
    global curio_checkpoint_if_cancelled

    try:
        from curio import check_cancellation as curio_checkpoint_if_cancelled
    except ImportError:

        async def curio_checkpoint_if_cancelled():
            pass

    await curio_checkpoint_if_cancelled()


async def trio_checkpoint_if_cancelled():
    global trio_checkpoint_if_cancelled

    try:
        from anyio.lowlevel import (
            checkpoint_if_cancelled as trio_checkpoint_if_cancelled,
        )
    except ImportError:
        try:
            from trio.lowlevel import (
                checkpoint_if_cancelled as trio_checkpoint_if_cancelled,
            )
        except ImportError:

            async def trio_checkpoint_if_cancelled():
                pass

    await trio_checkpoint_if_cancelled()


async def asyncio_cancel_shielded_checkpoint():
    global asyncio_cancel_shielded_checkpoint

    try:
        from anyio.lowlevel import (
            cancel_shielded_checkpoint as asyncio_cancel_shielded_checkpoint,
        )
    except ImportError:
        try:
            from asyncio import (
                sleep as asyncio_sleep,
                shield as asyncio_shield,
            )
        except ImportError:

            async def asyncio_cancel_shielded_checkpoint():
                pass

        else:

            async def asyncio_cancel_shielded_checkpoint():
                await asyncio_shield(asyncio_sleep(0))

    await asyncio_cancel_shielded_checkpoint()


async def curio_cancel_shielded_checkpoint():
    global curio_cancel_shielded_checkpoint

    try:
        from curio import (
            sleep as curio_sleep,
            disable_cancellation as curio_disable_cancellation,
        )
    except ImportError:

        async def curio_cancel_shielded_checkpoint():
            pass

    else:

        async def curio_cancel_shielded_checkpoint():
            async with curio_disable_cancellation():
                await curio_sleep(0)

    await curio_cancel_shielded_checkpoint()


async def trio_cancel_shielded_checkpoint():
    global trio_cancel_shielded_checkpoint

    try:
        from anyio.lowlevel import (
            cancel_shielded_checkpoint as trio_cancel_shielded_checkpoint,
        )
    except ImportError:
        try:
            from trio.lowlevel import (
                cancel_shielded_checkpoint as trio_cancel_shielded_checkpoint,
            )
        except ImportError:

            async def trio_cancel_shielded_checkpoint():
                pass

    await trio_cancel_shielded_checkpoint()


async def shield(coro):
    library = current_async_library()

    if library == "asyncio":
        result = await asyncio_shield(coro)
    elif library == "curio":
        result = await curio_shield(coro)
    elif library == "trio":
        result = await trio_shield(coro)
    else:
        raise RuntimeError(f"unsupported async library {library!r}")

    return result


async def checkpoint(*, force=False):
    try:
        library = current_async_library()
    except AsyncLibraryNotFoundError:
        pass
    else:
        if library == "asyncio":
            if force or asyncio_checkpoints_cvar.get():
                await asyncio_checkpoint()
        elif library == "curio":
            if force or curio_checkpoints_cvar.get():
                await curio_checkpoint()
        elif library == "trio":
            if force or trio_checkpoints_cvar.get():
                await trio_checkpoint()


async def checkpoint_if_cancelled(*, force=False):
    try:
        library = current_async_library()
    except AsyncLibraryNotFoundError:
        pass
    else:
        if library == "asyncio":
            if force or asyncio_checkpoints_cvar.get():
                await asyncio_checkpoint_if_cancelled()
        elif library == "curio":
            if force or curio_checkpoints_cvar.get():
                await curio_checkpoint_if_cancelled()
        elif library == "trio":
            if force or trio_checkpoints_cvar.get():
                await trio_checkpoint_if_cancelled()


async def cancel_shielded_checkpoint(*, force=False):
    try:
        library = current_async_library()
    except AsyncLibraryNotFoundError:
        pass
    else:
        if library == "asyncio":
            if force or asyncio_checkpoints_cvar.get():
                await asyncio_cancel_shielded_checkpoint()
        elif library == "curio":
            if force or curio_checkpoints_cvar.get():
                await curio_cancel_shielded_checkpoint()
        elif library == "trio":
            if force or trio_checkpoints_cvar.get():
                await trio_cancel_shielded_checkpoint()
