#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import os
import sys

from contextvars import ContextVar
from inspect import isawaitable, iscoroutinefunction

from wrapt import ObjectProxy, decorator, when_imported

from . import _time
from ._ident import current_thread_ident
from ._libraries import current_async_library, current_green_library
from ._markers import MISSING

if sys.version_info >= (3, 13):
    from warnings import deprecated
else:
    from typing_extensions import deprecated

THREADING_CHECKPOINTS_ENABLED = bool(
    os.getenv(
        "AIOLOGIC_THREADING_CHECKPOINTS",
        "1" if os.getenv("AIOLOGIC_GREEN_CHECKPOINTS", "") else "",
    )
)
EVENTLET_CHECKPOINTS_ENABLED = bool(
    os.getenv(
        "AIOLOGIC_EVENTLET_CHECKPOINTS",
        "1" if os.getenv("AIOLOGIC_GREEN_CHECKPOINTS", "") else "",
    )
)
GEVENT_CHECKPOINTS_ENABLED = bool(
    os.getenv(
        "AIOLOGIC_GEVENT_CHECKPOINTS",
        "1" if os.getenv("AIOLOGIC_GREEN_CHECKPOINTS", "") else "",
    )
)
ASYNCIO_CHECKPOINTS_ENABLED = bool(
    os.getenv(
        "AIOLOGIC_ASYNCIO_CHECKPOINTS",
        "1" if os.getenv("AIOLOGIC_ASYNC_CHECKPOINTS", "") else "",
    )
)
CURIO_CHECKPOINTS_ENABLED = bool(
    os.getenv(
        "AIOLOGIC_CURIO_CHECKPOINTS",
        "1" if os.getenv("AIOLOGIC_ASYNC_CHECKPOINTS", "") else "",
    )
)
TRIO_CHECKPOINTS_ENABLED = bool(
    os.getenv(
        "AIOLOGIC_TRIO_CHECKPOINTS",
        "1" if os.getenv("AIOLOGIC_ASYNC_CHECKPOINTS", "1") else "",
    )
)


def _threading_checkpoints_enabled():
    return THREADING_CHECKPOINTS_ENABLED


def _eventlet_checkpoints_enabled():
    return EVENTLET_CHECKPOINTS_ENABLED


def _gevent_checkpoints_enabled():
    return GEVENT_CHECKPOINTS_ENABLED


def _asyncio_checkpoints_enabled():
    return ASYNCIO_CHECKPOINTS_ENABLED


def _curio_checkpoints_enabled():
    return CURIO_CHECKPOINTS_ENABLED


def _trio_checkpoints_enabled():
    return TRIO_CHECKPOINTS_ENABLED


def green_checkpoint_enabled():
    if _green_checkpoints_enabled:
        library = current_green_library(failsafe=True)

        if library == "threading":
            return _threading_checkpoints_enabled()
        elif library == "eventlet":
            return _eventlet_checkpoints_enabled()
        elif library == "gevent":
            return _gevent_checkpoints_enabled()

    return False


def async_checkpoint_enabled():
    if _async_checkpoints_enabled:
        library = current_async_library(failsafe=True)

        if library == "asyncio":
            return _asyncio_checkpoints_enabled()
        elif library == "curio":
            return _curio_checkpoints_enabled()
        elif library == "trio":
            return _trio_checkpoints_enabled()

    return False


_green_checkpoints_enabled = THREADING_CHECKPOINTS_ENABLED
_async_checkpoints_enabled = False


@when_imported("eventlet")
def _(_):
    global _green_checkpoints_enabled

    if EVENTLET_CHECKPOINTS_ENABLED:
        _green_checkpoints_enabled = True


@when_imported("gevent")
def _(_):
    global _green_checkpoints_enabled

    if GEVENT_CHECKPOINTS_ENABLED:
        _green_checkpoints_enabled = True


@when_imported("asyncio")
def _(_):
    global _async_checkpoints_enabled

    if ASYNCIO_CHECKPOINTS_ENABLED:
        _async_checkpoints_enabled = True


@when_imported("curio")
def _(_):
    global _async_checkpoints_enabled

    if CURIO_CHECKPOINTS_ENABLED:
        _async_checkpoints_enabled = True


@when_imported("trio")
def _(_):
    global _async_checkpoints_enabled

    if TRIO_CHECKPOINTS_ENABLED:
        _async_checkpoints_enabled = True


_green_checkpoints_cvar = ContextVar(
    "_green_checkpoints_cvar",
    default=(
        current_thread_ident(),
        None,
    ),
)
_async_checkpoints_cvar = ContextVar(
    "_async_checkpoints_cvar",
    default=(
        current_thread_ident(),
        None,
    ),
)


def _green_checkpoints_reset(token):
    pass


def _async_checkpoints_reset(token):
    pass


def _green_checkpoints_set(enabled):
    global _threading_checkpoints_enabled
    global _eventlet_checkpoints_enabled
    global _gevent_checkpoints_enabled

    global _green_checkpoints_enabled
    global _green_checkpoints_reset
    global _green_checkpoints_set

    if enabled or _green_checkpoints_enabled:

        def _threading_checkpoints_enabled():
            ident, enabled = _green_checkpoints_cvar.get()

            if enabled is None:
                return THREADING_CHECKPOINTS_ENABLED

            if ident != current_thread_ident():
                return THREADING_CHECKPOINTS_ENABLED

            return enabled

        def _eventlet_checkpoints_enabled():
            ident, enabled = _green_checkpoints_cvar.get()

            if enabled is None:
                return EVENTLET_CHECKPOINTS_ENABLED

            if ident != current_thread_ident():
                return EVENTLET_CHECKPOINTS_ENABLED

            return enabled

        def _gevent_checkpoints_enabled():
            ident, enabled = _green_checkpoints_cvar.get()

            if enabled is None:
                return GEVENT_CHECKPOINTS_ENABLED

            if ident != current_thread_ident():
                return GEVENT_CHECKPOINTS_ENABLED

            return enabled

        _green_checkpoints_enabled = True
        _green_checkpoints_reset = _green_checkpoints_cvar.reset

        def _green_checkpoints_set(enabled):
            return _green_checkpoints_cvar.set((
                current_thread_ident(),
                enabled,
            ))

        return _green_checkpoints_set(enabled)

    return None


def _async_checkpoints_set(enabled):
    global _asyncio_checkpoints_enabled
    global _curio_checkpoints_enabled
    global _trio_checkpoints_enabled

    global _async_checkpoints_enabled
    global _async_checkpoints_reset
    global _async_checkpoints_set

    if enabled or _async_checkpoints_enabled:

        def _asyncio_checkpoints_enabled():
            ident, enabled = _async_checkpoints_cvar.get()

            if enabled is None:
                return ASYNCIO_CHECKPOINTS_ENABLED

            if ident != current_thread_ident():
                return ASYNCIO_CHECKPOINTS_ENABLED

            return enabled

        def _curio_checkpoints_enabled():
            ident, enabled = _async_checkpoints_cvar.get()

            if enabled is None:
                return CURIO_CHECKPOINTS_ENABLED

            if ident != current_thread_ident():
                return CURIO_CHECKPOINTS_ENABLED

            return enabled

        def _trio_checkpoints_enabled():
            ident, enabled = _async_checkpoints_cvar.get()

            if enabled is None:
                return TRIO_CHECKPOINTS_ENABLED

            if ident != current_thread_ident():
                return TRIO_CHECKPOINTS_ENABLED

            return enabled

        _async_checkpoints_enabled = True
        _async_checkpoints_reset = _async_checkpoints_cvar.reset

        def _async_checkpoints_set(enabled):
            return _async_checkpoints_cvar.set((
                current_thread_ident(),
                enabled,
            ))

        return _async_checkpoints_set(enabled)

    return None


class _AwaitableWithCheckpoints(ObjectProxy):
    __slots__ = ()

    def __await__(self, /):
        token = _async_checkpoints_set(True)

        try:
            return (yield from self.__wrapped__.__await__())
        finally:
            _async_checkpoints_reset(token)


class _AwaitableWithoutCheckpoints(ObjectProxy):
    __slots__ = ()

    def __await__(self, /):
        token = _async_checkpoints_set(False)

        try:
            return (yield from self.__wrapped__.__await__())
        finally:
            _async_checkpoints_reset(token)


@decorator
async def _enable_async_checkpoints(wrapped, instance, args, kwargs, /):
    token = _async_checkpoints_set(True)

    try:
        return await wrapped(*args, **kwargs)
    finally:
        _async_checkpoints_reset(token)


@decorator
async def _disable_async_checkpoints(wrapped, instance, args, kwargs, /):
    token = _async_checkpoints_set(False)

    try:
        return await wrapped(*args, **kwargs)
    finally:
        _async_checkpoints_reset(token)


@decorator
def _enable_green_checkpoints(wrapped, instance, args, kwargs, /):
    token = _green_checkpoints_set(True)

    try:
        return wrapped(*args, **kwargs)
    finally:
        _green_checkpoints_reset(token)


@decorator
def _disable_green_checkpoints(wrapped, instance, args, kwargs, /):
    token = _green_checkpoints_set(False)

    try:
        return wrapped(*args, **kwargs)
    finally:
        _green_checkpoints_reset(token)


class enable_checkpoints:
    __slots__ = ("__token",)

    def __new__(cls, wrapped=MISSING, /):
        if wrapped is MISSING:
            return super().__new__(cls)
        elif isawaitable(wrapped):
            return _AwaitableWithCheckpoints(wrapped)
        elif iscoroutinefunction(wrapped):
            return _enable_async_checkpoints(wrapped)
        else:
            return _enable_green_checkpoints(wrapped)

    async def __aenter__(self, /):
        self.__token = _async_checkpoints_set(True)

        return True

    async def __aexit__(self, /, exc_type, exc_value, traceback):
        _async_checkpoints_reset(self.__token)

    def __enter__(self, /):
        self.__token = _green_checkpoints_set(True)

        return True

    def __exit__(self, /, exc_type, exc_value, traceback):
        _green_checkpoints_reset(self.__token)


class disable_checkpoints:
    __slots__ = ("__token",)

    def __new__(cls, wrapped=MISSING, /):
        if wrapped is MISSING:
            return super().__new__(cls)
        elif isawaitable(wrapped):
            return _AwaitableWithoutCheckpoints(wrapped)
        elif iscoroutinefunction(wrapped):
            return _disable_async_checkpoints(wrapped)
        else:
            return _disable_green_checkpoints(wrapped)

    async def __aenter__(self, /):
        self.__token = _async_checkpoints_set(False)

        return False

    async def __aexit__(self, /, exc_type, exc_value, traceback):
        _async_checkpoints_reset(self.__token)

    def __enter__(self, /):
        self.__token = _green_checkpoints_set(False)

        return False

    def __exit__(self, /, exc_type, exc_value, traceback):
        _green_checkpoints_reset(self.__token)


async def _trio_checkpoint():
    global _trio_checkpoint

    from trio.lowlevel import checkpoint as _trio_checkpoint

    await _trio_checkpoint()


def green_checkpoint(*, force=False):
    if _green_checkpoints_enabled or force:
        library = current_green_library(failsafe=True)

        if library == "threading":
            if force or _threading_checkpoints_enabled():
                _time._threading_sleep(0)
        elif library == "eventlet":
            if force or _eventlet_checkpoints_enabled():
                _time._eventlet_sleep()
        elif library == "gevent":
            if force or _gevent_checkpoints_enabled():
                _time._gevent_sleep()


@deprecated("Use async_checkpoint() instead")
async def checkpoint(*, force=False):
    if _async_checkpoints_enabled or force:
        library = current_async_library(failsafe=True)

        if library == "asyncio":
            if force or _asyncio_checkpoints_enabled():
                await _time._asyncio_sleep(0)
        elif library == "curio":
            if force or _curio_checkpoints_enabled():
                await _time._curio_sleep(0)
        elif library == "trio":
            if force or _trio_checkpoints_enabled():
                await _trio_checkpoint()


async def async_checkpoint(*, force=False):
    if _async_checkpoints_enabled or force:
        library = current_async_library(failsafe=True)

        if library == "asyncio":
            if force or _asyncio_checkpoints_enabled():
                await _time._asyncio_sleep(0)
        elif library == "curio":
            if force or _curio_checkpoints_enabled():
                await _time._curio_sleep(0)
        elif library == "trio":
            if force or _trio_checkpoints_enabled():
                await _trio_checkpoint()


async def _asyncio_checkpoint_if_cancelled():
    pass


@when_imported("anyio")
def _(_):
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


def green_checkpoint_if_cancelled(*, force=False):
    pass


async def async_checkpoint_if_cancelled(*, force=False):
    if _async_checkpoints_enabled or force:
        library = current_async_library(failsafe=True)

        if library == "asyncio":
            if force or _asyncio_checkpoints_enabled():
                await _asyncio_checkpoint_if_cancelled()
        elif library == "curio":
            if force or _curio_checkpoints_enabled():
                await _curio_checkpoint_if_cancelled()
        elif library == "trio":
            if force or _trio_checkpoints_enabled():
                await _trio_checkpoint_if_cancelled()
