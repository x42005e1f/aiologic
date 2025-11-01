#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import os
import sys
import warnings

from contextvars import ContextVar, Token
from inspect import isawaitable, iscoroutinefunction
from typing import TYPE_CHECKING, Any, Final, Literal, TypeVar

from wrapt import ObjectProxy, decorator, when_imported

from ._libraries import current_async_library, current_green_library
from ._markers import MISSING, MissingType
from ._threads import current_thread_ident
from ._utils import _replaces as replaces

if sys.version_info >= (3, 11):
    from typing import overload
else:
    from typing_extensions import overload

if sys.version_info >= (3, 9):
    from collections.abc import Awaitable, Callable
else:
    from typing import Awaitable, Callable

if TYPE_CHECKING:
    from types import TracebackType

_AwaitableT = TypeVar("_AwaitableT", bound=Awaitable[Any])
_CallableT = TypeVar("_CallableT", bound=Callable[..., Any])

_THREADING_CHECKPOINTS_ENABLED_BY_DEFAULT: Final[bool] = bool(
    os.getenv(
        "AIOLOGIC_THREADING_CHECKPOINTS",
        os.getenv(
            "AIOLOGIC_GREEN_CHECKPOINTS",
            "",
        ),
    )
)
_EVENTLET_CHECKPOINTS_ENABLED_BY_DEFAULT: Final[bool] = bool(
    os.getenv(
        "AIOLOGIC_EVENTLET_CHECKPOINTS",
        os.getenv(
            "AIOLOGIC_GREEN_CHECKPOINTS",
            "",
        ),
    )
)
_GEVENT_CHECKPOINTS_ENABLED_BY_DEFAULT: Final[bool] = bool(
    os.getenv(
        "AIOLOGIC_GEVENT_CHECKPOINTS",
        os.getenv(
            "AIOLOGIC_GREEN_CHECKPOINTS",
            "",
        ),
    )
)
_ASYNCIO_CHECKPOINTS_ENABLED_BY_DEFAULT: Final[bool] = bool(
    os.getenv(
        "AIOLOGIC_ASYNCIO_CHECKPOINTS",
        os.getenv(
            "AIOLOGIC_ASYNC_CHECKPOINTS",
            "",
        ),
    )
)
_CURIO_CHECKPOINTS_ENABLED_BY_DEFAULT: Final[bool] = bool(
    os.getenv(
        "AIOLOGIC_CURIO_CHECKPOINTS",
        os.getenv(
            "AIOLOGIC_ASYNC_CHECKPOINTS",
            "",
        ),
    )
)
_TRIO_CHECKPOINTS_ENABLED_BY_DEFAULT: Final[bool] = bool(
    os.getenv(
        "AIOLOGIC_TRIO_CHECKPOINTS",
        os.getenv(
            "AIOLOGIC_ASYNC_CHECKPOINTS",
            "1",
        ),
    )
)

_green_checkpoints_enabled: bool = _THREADING_CHECKPOINTS_ENABLED_BY_DEFAULT
_async_checkpoints_enabled: bool = False
_green_checkpoints_disabled: bool = not _green_checkpoints_enabled
_async_checkpoints_disabled: bool = False
_green_checkpoints_used: bool = False
_async_checkpoints_used: bool = False


@when_imported("eventlet")
def _(_):
    global _green_checkpoints_enabled
    global _green_checkpoints_disabled

    if _EVENTLET_CHECKPOINTS_ENABLED_BY_DEFAULT:
        _green_checkpoints_enabled = True
    else:
        _green_checkpoints_disabled = True


@when_imported("gevent")
def _(_):
    global _green_checkpoints_enabled
    global _green_checkpoints_disabled

    if _GEVENT_CHECKPOINTS_ENABLED_BY_DEFAULT:
        _green_checkpoints_enabled = True
    else:
        _green_checkpoints_disabled = True


@when_imported("asyncio")
def _(_):
    global _async_checkpoints_enabled
    global _async_checkpoints_disabled

    if _ASYNCIO_CHECKPOINTS_ENABLED_BY_DEFAULT:
        _async_checkpoints_enabled = True
    else:
        _async_checkpoints_disabled = True


@when_imported("curio")
def _(_):
    global _async_checkpoints_enabled
    global _async_checkpoints_disabled

    if _CURIO_CHECKPOINTS_ENABLED_BY_DEFAULT:
        _async_checkpoints_enabled = True
    else:
        _async_checkpoints_disabled = True


@when_imported("trio")
def _(_):
    global _async_checkpoints_enabled
    global _async_checkpoints_disabled

    if _TRIO_CHECKPOINTS_ENABLED_BY_DEFAULT:
        _async_checkpoints_enabled = True
    else:
        _async_checkpoints_disabled = True


_green_checkpoints_cvar: ContextVar[tuple[int, bool | None]] = ContextVar(
    "_green_checkpoints_cvar",
    default=(
        current_thread_ident(),
        None,
    ),
)
_async_checkpoints_cvar: ContextVar[tuple[int, bool | None]] = ContextVar(
    "_async_checkpoints_cvar",
    default=(
        current_thread_ident(),
        None,
    ),
)


def _threading_checkpoints_enabled() -> bool:
    return _THREADING_CHECKPOINTS_ENABLED_BY_DEFAULT


def _eventlet_checkpoints_enabled() -> bool:
    return _EVENTLET_CHECKPOINTS_ENABLED_BY_DEFAULT


def _gevent_checkpoints_enabled() -> bool:
    return _GEVENT_CHECKPOINTS_ENABLED_BY_DEFAULT


def _asyncio_checkpoints_enabled() -> bool:
    return _ASYNCIO_CHECKPOINTS_ENABLED_BY_DEFAULT


def _curio_checkpoints_enabled() -> bool:
    return _CURIO_CHECKPOINTS_ENABLED_BY_DEFAULT


def _trio_checkpoints_enabled() -> bool:
    return _TRIO_CHECKPOINTS_ENABLED_BY_DEFAULT


def _green_checkpoints_reset(token: Token[tuple[int, bool | None]], /) -> None:
    pass


def _async_checkpoints_reset(token: Token[tuple[int, bool | None]], /) -> None:
    pass


def _green_checkpoints_set(enabled: bool) -> Token[tuple[int, bool | None]]:
    global _green_checkpoints_used

    @replaces(globals())
    def _threading_checkpoints_enabled():
        ident, maybe_enabled = _green_checkpoints_cvar.get()

        if maybe_enabled is None or ident != current_thread_ident():
            return _THREADING_CHECKPOINTS_ENABLED_BY_DEFAULT

        return maybe_enabled

    @replaces(globals())
    def _eventlet_checkpoints_enabled():
        ident, maybe_enabled = _green_checkpoints_cvar.get()

        if maybe_enabled is None or ident != current_thread_ident():
            return _EVENTLET_CHECKPOINTS_ENABLED_BY_DEFAULT

        return maybe_enabled

    @replaces(globals())
    def _gevent_checkpoints_enabled():
        ident, maybe_enabled = _green_checkpoints_cvar.get()

        if maybe_enabled is None or ident != current_thread_ident():
            return _GEVENT_CHECKPOINTS_ENABLED_BY_DEFAULT

        return maybe_enabled

    _green_checkpoints_used = True

    @replaces(globals())
    def _green_checkpoints_reset(
        token: Token[tuple[int, bool | None]],
        /,
    ) -> None:
        _green_checkpoints_cvar.reset(token)

    @replaces(globals())
    def _green_checkpoints_set(enabled):
        return _green_checkpoints_cvar.set((
            current_thread_ident(),
            enabled,
        ))

    return _green_checkpoints_set(enabled)


def _async_checkpoints_set(enabled: bool) -> Token[tuple[int, bool | None]]:
    global _async_checkpoints_used

    @replaces(globals())
    def _asyncio_checkpoints_enabled():
        ident, maybe_enabled = _async_checkpoints_cvar.get()

        if maybe_enabled is None or ident != current_thread_ident():
            return _ASYNCIO_CHECKPOINTS_ENABLED_BY_DEFAULT

        return maybe_enabled

    @replaces(globals())
    def _curio_checkpoints_enabled():
        ident, maybe_enabled = _async_checkpoints_cvar.get()

        if maybe_enabled is None or ident != current_thread_ident():
            return _CURIO_CHECKPOINTS_ENABLED_BY_DEFAULT

        return maybe_enabled

    @replaces(globals())
    def _trio_checkpoints_enabled():
        ident, maybe_enabled = _async_checkpoints_cvar.get()

        if maybe_enabled is None or ident != current_thread_ident():
            return _TRIO_CHECKPOINTS_ENABLED_BY_DEFAULT

        return maybe_enabled

    _async_checkpoints_used = True

    @replaces(globals())
    def _async_checkpoints_reset(
        token: Token[tuple[int, bool | None]],
        /,
    ) -> None:
        _async_checkpoints_cvar.reset(token)

    @replaces(globals())
    def _async_checkpoints_set(enabled):
        return _async_checkpoints_cvar.set((
            current_thread_ident(),
            enabled,
        ))

    return _async_checkpoints_set(enabled)


def green_checkpoint_enabled() -> bool:
    """..."""

    if _green_checkpoints_used:
        ident, maybe_enabled = _green_checkpoints_cvar.get()

        if maybe_enabled is not None and ident == current_thread_ident():
            return maybe_enabled

    if _green_checkpoints_enabled and _green_checkpoints_disabled:
        library = current_green_library(failsafe=True)

        if library == "threading":
            return _THREADING_CHECKPOINTS_ENABLED_BY_DEFAULT

        if library == "eventlet":
            return _EVENTLET_CHECKPOINTS_ENABLED_BY_DEFAULT

        if library == "gevent":
            return _GEVENT_CHECKPOINTS_ENABLED_BY_DEFAULT

    return _green_checkpoints_enabled


def async_checkpoint_enabled() -> bool:
    """..."""

    if _async_checkpoints_used:
        ident, maybe_enabled = _async_checkpoints_cvar.get()

        if maybe_enabled is not None and ident == current_thread_ident():
            return maybe_enabled

    if _async_checkpoints_enabled and _async_checkpoints_disabled:
        library = current_async_library(failsafe=True)

        if library == "asyncio":
            return _ASYNCIO_CHECKPOINTS_ENABLED_BY_DEFAULT

        if library == "curio":
            return _CURIO_CHECKPOINTS_ENABLED_BY_DEFAULT

        if library == "trio":
            return _TRIO_CHECKPOINTS_ENABLED_BY_DEFAULT

    return _async_checkpoints_enabled


class _CheckpointsManager:
    __slots__ = ("__token",)

    async def __aenter__(self, /) -> Literal[True]:
        self.__token = _async_checkpoints_set(True)

        return True

    def __enter__(self, /) -> Literal[True]:
        self.__token = _green_checkpoints_set(True)

        return True

    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        _async_checkpoints_reset(self.__token)

    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        _green_checkpoints_reset(self.__token)


class _NoCheckpointsManager:
    __slots__ = ("__token",)

    async def __aenter__(self, /) -> Literal[False]:
        self.__token = _async_checkpoints_set(False)

        return False

    def __enter__(self, /) -> Literal[False]:
        self.__token = _green_checkpoints_set(False)

        return False

    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        _async_checkpoints_reset(self.__token)

    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        _green_checkpoints_reset(self.__token)


class __AwaitableWithCheckpoints(ObjectProxy):
    __slots__ = ()

    def __await__(self, /):
        token = _async_checkpoints_set(True)

        try:
            return (yield from self.__wrapped__.__await__())
        except BaseException:
            self = None  # noqa: PLW0642
            raise
        finally:
            _async_checkpoints_reset(token)


class __AwaitableWithNoCheckpoints(ObjectProxy):
    __slots__ = ()

    def __await__(self, /):
        token = _async_checkpoints_set(False)

        try:
            return (yield from self.__wrapped__.__await__())
        except BaseException:
            self = None  # noqa: PLW0642
            raise
        finally:
            _async_checkpoints_reset(token)


@decorator
async def __enable_async_checkpoints(wrapped, instance, args, kwargs, /):
    token = _async_checkpoints_set(True)

    try:
        return await wrapped(*args, **kwargs)
    finally:
        _async_checkpoints_reset(token)


@decorator
async def __disable_async_checkpoints(wrapped, instance, args, kwargs, /):
    token = _async_checkpoints_set(False)

    try:
        return await wrapped(*args, **kwargs)
    finally:
        _async_checkpoints_reset(token)


@decorator
def __enable_green_checkpoints(wrapped, instance, args, kwargs, /):
    token = _green_checkpoints_set(True)

    try:
        return wrapped(*args, **kwargs)
    finally:
        _green_checkpoints_reset(token)


@decorator
def __disable_green_checkpoints(wrapped, instance, args, kwargs, /):
    token = _green_checkpoints_set(False)

    try:
        return wrapped(*args, **kwargs)
    finally:
        _green_checkpoints_reset(token)


@overload
def enable_checkpoints(
    wrapped: MissingType = MISSING,
    /,
) -> _CheckpointsManager: ...
@overload
def enable_checkpoints(wrapped: _AwaitableT, /) -> _AwaitableT: ...
@overload
def enable_checkpoints(wrapped: _CallableT, /) -> _CallableT: ...
def enable_checkpoints(wrapped=MISSING, /):
    """..."""

    if wrapped is MISSING:
        return _CheckpointsManager()

    if isawaitable(wrapped):
        return __AwaitableWithCheckpoints(wrapped)

    if iscoroutinefunction(wrapped):
        return __enable_async_checkpoints(wrapped)

    return __enable_green_checkpoints(wrapped)


@overload
def disable_checkpoints(
    wrapped: MissingType = MISSING,
    /,
) -> _NoCheckpointsManager: ...
@overload
def disable_checkpoints(wrapped: _AwaitableT, /) -> _AwaitableT: ...
@overload
def disable_checkpoints(wrapped: _CallableT, /) -> _CallableT: ...
def disable_checkpoints(wrapped=MISSING, /):
    """..."""

    if wrapped is MISSING:
        return _NoCheckpointsManager()

    if isawaitable(wrapped):
        return __AwaitableWithNoCheckpoints(wrapped)

    if iscoroutinefunction(wrapped):
        return __disable_async_checkpoints(wrapped)

    return __disable_green_checkpoints(wrapped)


def _threading_checkpoint() -> None:
    global _threading_checkpoint

    from . import _monkey

    if hasattr(os, "sched_yield") and (
        sys.version_info >= (3, 11, 1)  # python/cpython#96078
        or (sys.version_info < (3, 11) and sys.version_info >= (3, 10, 8))
    ):
        _threading_checkpoint = _monkey._import_original("os", "sched_yield")
    else:
        _sleep = _monkey._import_original("time", "sleep")

        @replaces(globals())
        def _threading_checkpoint():
            _sleep(0)

    _threading_checkpoint()


def _eventlet_checkpoint() -> None:
    global _eventlet_checkpoint

    from eventlet import sleep as _eventlet_checkpoint

    _eventlet_checkpoint()


def _gevent_checkpoint() -> None:
    global _gevent_checkpoint

    from gevent import sleep as _gevent_checkpoint

    _gevent_checkpoint()


async def _asyncio_checkpoint() -> None:
    from types import coroutine

    @coroutine
    def _asyncio_checkpoint():
        yield

    await _asyncio_checkpoint()


async def _curio_checkpoint() -> None:
    from curio import sleep

    @replaces(globals())
    async def _curio_checkpoint():
        await sleep(0)

    await _curio_checkpoint()


async def _trio_checkpoint() -> None:
    global _trio_checkpoint

    from trio.lowlevel import checkpoint as _trio_checkpoint

    await _trio_checkpoint()


def green_checkpoint(*, force: bool = False) -> None:
    """..."""

    if not force:
        if _green_checkpoints_enabled and _green_checkpoints_disabled:
            enabled = None
        else:
            enabled = _green_checkpoints_enabled

        if _green_checkpoints_used:
            ident, maybe_enabled = _green_checkpoints_cvar.get()

            if maybe_enabled is not None and ident == current_thread_ident():
                enabled = maybe_enabled
    else:
        enabled = True

    if enabled is None or enabled:
        library = current_green_library(failsafe=True)

        if library == "threading":
            if enabled is None:
                enabled = _THREADING_CHECKPOINTS_ENABLED_BY_DEFAULT

            if enabled:
                _threading_checkpoint()
        elif library == "eventlet":
            if enabled is None:
                enabled = _EVENTLET_CHECKPOINTS_ENABLED_BY_DEFAULT

            if enabled:
                _eventlet_checkpoint()
        elif library == "gevent":
            if enabled is None:
                enabled = _GEVENT_CHECKPOINTS_ENABLED_BY_DEFAULT

            if enabled:
                _gevent_checkpoint()


async def checkpoint(*, force: bool = False) -> None:
    warnings.warn(
        "Use async_checkpoint() instead",
        DeprecationWarning,
        stacklevel=2,
    )

    await async_checkpoint(force=force)


async def async_checkpoint(*, force: bool = False) -> None:
    """..."""

    if not force:
        if _async_checkpoints_enabled and _async_checkpoints_disabled:
            enabled = None
        else:
            enabled = _async_checkpoints_enabled

        if _async_checkpoints_used:
            ident, maybe_enabled = _async_checkpoints_cvar.get()

            if maybe_enabled is not None and ident == current_thread_ident():
                enabled = maybe_enabled
    else:
        enabled = True

    if enabled is None or enabled:
        library = current_async_library(failsafe=True)

        if library == "asyncio":
            if enabled is None:
                enabled = _ASYNCIO_CHECKPOINTS_ENABLED_BY_DEFAULT

            if enabled:
                await _asyncio_checkpoint()
        elif library == "curio":
            if enabled is None:
                enabled = _CURIO_CHECKPOINTS_ENABLED_BY_DEFAULT

            if enabled:
                await _curio_checkpoint()
        elif library == "trio":
            if enabled is None:
                enabled = _TRIO_CHECKPOINTS_ENABLED_BY_DEFAULT

            if enabled:
                await _trio_checkpoint()


async def _asyncio_checkpoint_if_cancelled() -> None:
    pass


@when_imported("anyio")
def _(_):
    @replaces(globals())
    async def _asyncio_checkpoint_if_cancelled():
        global _asyncio_checkpoint_if_cancelled

        from anyio.lowlevel import checkpoint_if_cancelled

        _asyncio_checkpoint_if_cancelled = checkpoint_if_cancelled

        await _asyncio_checkpoint_if_cancelled()


async def _curio_checkpoint_if_cancelled() -> None:
    global _curio_checkpoint_if_cancelled

    from curio import check_cancellation as _curio_checkpoint_if_cancelled

    await _curio_checkpoint_if_cancelled()


async def _trio_checkpoint_if_cancelled() -> None:
    global _trio_checkpoint_if_cancelled

    from trio.lowlevel import checkpoint_if_cancelled

    _trio_checkpoint_if_cancelled = checkpoint_if_cancelled

    await _trio_checkpoint_if_cancelled()


def green_checkpoint_if_cancelled(*, force: bool = False) -> None:
    """..."""


async def async_checkpoint_if_cancelled(*, force: bool = False) -> None:
    """..."""

    if not force:
        if _async_checkpoints_enabled and _async_checkpoints_disabled:
            enabled = None
        else:
            enabled = _async_checkpoints_enabled

        if _async_checkpoints_used:
            ident, maybe_enabled = _async_checkpoints_cvar.get()

            if maybe_enabled is not None and ident == current_thread_ident():
                enabled = maybe_enabled
    else:
        enabled = True

    if enabled is None or enabled:
        library = current_async_library(failsafe=True)

        if library == "asyncio":
            if enabled is None:
                enabled = _ASYNCIO_CHECKPOINTS_ENABLED_BY_DEFAULT

            if enabled:
                await _asyncio_checkpoint_if_cancelled()
        elif library == "curio":
            if enabled is None:
                enabled = _CURIO_CHECKPOINTS_ENABLED_BY_DEFAULT

            if enabled:
                await _curio_checkpoint_if_cancelled()
        elif library == "trio":
            if enabled is None:
                enabled = _TRIO_CHECKPOINTS_ENABLED_BY_DEFAULT

            if enabled:
                await _trio_checkpoint_if_cancelled()
