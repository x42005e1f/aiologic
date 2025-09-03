#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import os
import sys
import warnings

from contextvars import ContextVar, Token
from inspect import isawaitable, iscoroutinefunction
from typing import TYPE_CHECKING, Any, Final, Literal, TypeVar, overload

from wrapt import ObjectProxy, decorator, when_imported

from . import _time
from ._libraries import current_async_library, current_green_library
from ._markers import MISSING, MissingType
from ._threads import current_thread_ident
from ._utils import _external as external, _replaces as replaces

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


_green_checkpoints_enabled_by_default: bool = (
    _THREADING_CHECKPOINTS_ENABLED_BY_DEFAULT
)
_async_checkpoints_enabled_by_default: bool = False
_green_checkpoints_used: list[None] = []
_async_checkpoints_used: list[None] = []


@when_imported("eventlet")
def _(_):
    global _green_checkpoints_enabled_by_default

    if _EVENTLET_CHECKPOINTS_ENABLED_BY_DEFAULT:
        _green_checkpoints_enabled_by_default = True
        _green_checkpoints_used.clear()


@when_imported("gevent")
def _(_):
    global _green_checkpoints_enabled_by_default

    if _GEVENT_CHECKPOINTS_ENABLED_BY_DEFAULT:
        _green_checkpoints_enabled_by_default = True
        _green_checkpoints_used.clear()


@when_imported("asyncio")
def _(_):
    global _async_checkpoints_enabled_by_default

    if _ASYNCIO_CHECKPOINTS_ENABLED_BY_DEFAULT:
        _async_checkpoints_enabled_by_default = True
        _async_checkpoints_used.clear()


@when_imported("curio")
def _(_):
    global _async_checkpoints_enabled_by_default

    if _CURIO_CHECKPOINTS_ENABLED_BY_DEFAULT:
        _async_checkpoints_enabled_by_default = True
        _async_checkpoints_used.clear()


@when_imported("trio")
def _(_):
    global _async_checkpoints_enabled_by_default

    if _TRIO_CHECKPOINTS_ENABLED_BY_DEFAULT:
        _async_checkpoints_enabled_by_default = True
        _async_checkpoints_used.clear()


def green_checkpoint_enabled() -> bool:
    """..."""

    if _green_checkpoints_enabled_by_default or _green_checkpoints_used:
        library = current_green_library(failsafe=True)

        if library == "threading":
            return _threading_checkpoints_enabled()

        if library == "eventlet":
            return _eventlet_checkpoints_enabled()

        if library == "gevent":
            return _gevent_checkpoints_enabled()

    return False


def async_checkpoint_enabled() -> bool:
    """..."""

    if _async_checkpoints_enabled_by_default or _async_checkpoints_used:
        library = current_async_library(failsafe=True)

        if library == "asyncio":
            return _asyncio_checkpoints_enabled()

        if library == "curio":
            return _curio_checkpoints_enabled()

        if library == "trio":
            return _trio_checkpoints_enabled()

    return False


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

_green_checkpoints_cvar_default_token: Token[tuple[int, bool | None]] = (
    _green_checkpoints_cvar.set(_green_checkpoints_cvar.get())
)
_async_checkpoints_cvar_default_token: Token[tuple[int, bool | None]] = (
    _async_checkpoints_cvar.set(_async_checkpoints_cvar.get())
)

_green_checkpoints_cvar.reset(_green_checkpoints_cvar_default_token)
_async_checkpoints_cvar.reset(_async_checkpoints_cvar_default_token)


def _green_checkpoints_reset(token: Token[tuple[int, bool | None]], /) -> None:
    pass


def _async_checkpoints_reset(token: Token[tuple[int, bool | None]], /) -> None:
    pass


def _green_checkpoints_set(enabled: bool) -> Token[tuple[int, bool | None]]:
    if enabled or _green_checkpoints_enabled_by_default:

        @replaces(globals())
        def _threading_checkpoints_enabled():
            ident, enabled = _green_checkpoints_cvar.get()

            if enabled is None:
                return _THREADING_CHECKPOINTS_ENABLED_BY_DEFAULT

            if ident != current_thread_ident():
                return _THREADING_CHECKPOINTS_ENABLED_BY_DEFAULT

            return enabled

        @replaces(globals())
        def _eventlet_checkpoints_enabled():
            ident, enabled = _green_checkpoints_cvar.get()

            if enabled is None:
                return _EVENTLET_CHECKPOINTS_ENABLED_BY_DEFAULT

            if ident != current_thread_ident():
                return _EVENTLET_CHECKPOINTS_ENABLED_BY_DEFAULT

            return enabled

        @replaces(globals())
        def _gevent_checkpoints_enabled():
            ident, enabled = _green_checkpoints_cvar.get()

            if enabled is None:
                return _GEVENT_CHECKPOINTS_ENABLED_BY_DEFAULT

            if ident != current_thread_ident():
                return _GEVENT_CHECKPOINTS_ENABLED_BY_DEFAULT

            return enabled

        @replaces(globals())
        def _green_checkpoints_reset(
            token: Token[tuple[int, bool | None]],
            /,
        ) -> None:
            if token is not _green_checkpoints_cvar_default_token:
                if not _green_checkpoints_enabled_by_default:
                    ident, enabled = _green_checkpoints_cvar.get()

                    if token.old_value is not token.MISSING:
                        was_enabled = token.old_value[1]

                        if was_enabled is None:
                            was_enabled = False

                        if token.old_value[0] != ident:
                            was_enabled = False
                    else:
                        was_enabled = False

                    if was_enabled != enabled:
                        if enabled:
                            try:
                                _green_checkpoints_used.pop()
                            except IndexError:
                                pass
                        else:
                            _green_checkpoints_used.append(None)

                            if _green_checkpoints_enabled_by_default:
                                _green_checkpoints_used.clear()

                _green_checkpoints_cvar.reset(token)

        @replaces(globals())
        def _green_checkpoints_set(enabled):
            token = _green_checkpoints_cvar.set((
                ident := current_thread_ident(),
                enabled,
            ))

            if not _green_checkpoints_enabled_by_default:
                if token.old_value is not token.MISSING:
                    was_enabled = token.old_value[1]

                    if was_enabled is None:
                        was_enabled = False

                    if token.old_value[0] != ident:
                        was_enabled = False
                else:
                    was_enabled = False

                if was_enabled != enabled:
                    if enabled:
                        _green_checkpoints_used.append(None)

                        if _green_checkpoints_enabled_by_default:
                            _green_checkpoints_used.clear()
                    else:
                        try:
                            _green_checkpoints_used.pop()
                        except IndexError:
                            pass

            return token

        return _green_checkpoints_set(enabled)

    return _green_checkpoints_cvar_default_token


def _async_checkpoints_set(enabled: bool) -> Token[tuple[int, bool | None]]:
    if enabled or _async_checkpoints_enabled_by_default:

        @replaces(globals())
        def _asyncio_checkpoints_enabled():
            ident, enabled = _async_checkpoints_cvar.get()

            if enabled is None:
                return _ASYNCIO_CHECKPOINTS_ENABLED_BY_DEFAULT

            if ident != current_thread_ident():
                return _ASYNCIO_CHECKPOINTS_ENABLED_BY_DEFAULT

            return enabled

        @replaces(globals())
        def _curio_checkpoints_enabled():
            ident, enabled = _async_checkpoints_cvar.get()

            if enabled is None:
                return _CURIO_CHECKPOINTS_ENABLED_BY_DEFAULT

            if ident != current_thread_ident():
                return _CURIO_CHECKPOINTS_ENABLED_BY_DEFAULT

            return enabled

        @replaces(globals())
        def _trio_checkpoints_enabled():
            ident, enabled = _async_checkpoints_cvar.get()

            if enabled is None:
                return _TRIO_CHECKPOINTS_ENABLED_BY_DEFAULT

            if ident != current_thread_ident():
                return _TRIO_CHECKPOINTS_ENABLED_BY_DEFAULT

            return enabled

        @replaces(globals())
        def _async_checkpoints_reset(
            token: Token[tuple[int, bool | None]],
            /,
        ) -> None:
            if token is not _async_checkpoints_cvar_default_token:
                if not _async_checkpoints_enabled_by_default:
                    ident, enabled = _async_checkpoints_cvar.get()

                    if token.old_value is not token.MISSING:
                        was_enabled = token.old_value[1]

                        if was_enabled is None:
                            was_enabled = False

                        if token.old_value[0] != ident:
                            was_enabled = False
                    else:
                        was_enabled = False

                    if was_enabled != enabled:
                        if enabled:
                            try:
                                _async_checkpoints_used.pop()
                            except IndexError:
                                pass
                        else:
                            _async_checkpoints_used.append(None)

                            if _async_checkpoints_enabled_by_default:
                                _async_checkpoints_used.clear()

                _async_checkpoints_cvar.reset(token)

        @replaces(globals())
        def _async_checkpoints_set(enabled):
            token = _async_checkpoints_cvar.set((
                ident := current_thread_ident(),
                enabled,
            ))

            if not _async_checkpoints_enabled_by_default:
                if token.old_value is not token.MISSING:
                    was_enabled = token.old_value[1]

                    if was_enabled is None:
                        was_enabled = False

                    if token.old_value[0] != ident:
                        was_enabled = False
                else:
                    was_enabled = False

                if was_enabled != enabled:
                    if enabled:
                        _async_checkpoints_used.append(None)

                        if _async_checkpoints_enabled_by_default:
                            _async_checkpoints_used.clear()
                    else:
                        try:
                            _async_checkpoints_used.pop()
                        except IndexError:
                            pass

            return token

        return _async_checkpoints_set(enabled)

    return _async_checkpoints_cvar_default_token


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
@external
def enable_checkpoints(
    wrapped: MissingType = MISSING,
    /,
) -> _CheckpointsManager: ...
@overload
@external
def enable_checkpoints(wrapped: _AwaitableT, /) -> _AwaitableT: ...
@overload
@external
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
@external
def disable_checkpoints(
    wrapped: MissingType = MISSING,
    /,
) -> _NoCheckpointsManager: ...
@overload
@external
def disable_checkpoints(wrapped: _AwaitableT, /) -> _AwaitableT: ...
@overload
@external
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


async def _trio_checkpoint() -> None:
    global _trio_checkpoint

    from trio.lowlevel import checkpoint as _trio_checkpoint

    await _trio_checkpoint()


def green_checkpoint(*, force: bool = False) -> None:
    """..."""

    if (
        force
        or _green_checkpoints_enabled_by_default
        or _green_checkpoints_used
    ):
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


async def checkpoint(*, force: bool = False) -> None:
    warnings.warn(
        "Use async_checkpoint() instead",
        DeprecationWarning,
        stacklevel=2,
    )

    if (
        force
        or _async_checkpoints_enabled_by_default
        or _async_checkpoints_used
    ):
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


async def async_checkpoint(*, force: bool = False) -> None:
    """..."""

    if (
        force
        or _async_checkpoints_enabled_by_default
        or _async_checkpoints_used
    ):
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

    if (
        force
        or _async_checkpoints_enabled_by_default
        or _async_checkpoints_used
    ):
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
