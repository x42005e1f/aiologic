#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from contextvars import ContextVar, Token
from types import TracebackType
from typing import Any, Final, Literal, TypeVar

from aiologic.meta import MISSING, MissingType

if sys.version_info >= (3, 11):
    from typing import overload
else:
    from typing_extensions import overload

if sys.version_info >= (3, 9):
    from collections.abc import Awaitable, Callable
else:
    from typing import Awaitable, Callable

_AwaitableT = TypeVar("_AwaitableT", bound=Awaitable[Any])
_CallableT = TypeVar("_CallableT", bound=Callable[..., Any])

_THREADING_CHECKPOINTS_ENABLED_BY_DEFAULT: Final[bool]
_EVENTLET_CHECKPOINTS_ENABLED_BY_DEFAULT: Final[bool]
_GEVENT_CHECKPOINTS_ENABLED_BY_DEFAULT: Final[bool]
_ASYNCIO_CHECKPOINTS_ENABLED_BY_DEFAULT: Final[bool]
_CURIO_CHECKPOINTS_ENABLED_BY_DEFAULT: Final[bool]
_TRIO_CHECKPOINTS_ENABLED_BY_DEFAULT: Final[bool]

_green_checkpoints_enabled: bool
_async_checkpoints_enabled: bool
_green_checkpoints_disabled: bool
_async_checkpoints_disabled: bool
_green_checkpoints_used: bool
_async_checkpoints_used: bool

_green_checkpoints_cvar: ContextVar[tuple[int, bool | None]]
_async_checkpoints_cvar: ContextVar[tuple[int, bool | None]]

def _threading_checkpoints_enabled() -> bool: ...
def _eventlet_checkpoints_enabled() -> bool: ...
def _gevent_checkpoints_enabled() -> bool: ...
def _asyncio_checkpoints_enabled() -> bool: ...
def _curio_checkpoints_enabled() -> bool: ...
def _trio_checkpoints_enabled() -> bool: ...
def _green_checkpoints_reset(
    token: Token[tuple[int, bool | None]],
    /,
) -> None: ...
def _async_checkpoints_reset(
    token: Token[tuple[int, bool | None]],
    /,
) -> None: ...
def _green_checkpoints_set(
    enabled: bool,
) -> Token[tuple[int, bool | None]]: ...
def _async_checkpoints_set(
    enabled: bool,
) -> Token[tuple[int, bool | None]]: ...
def green_checkpoint_enabled() -> bool: ...
def async_checkpoint_enabled() -> bool: ...

class _CheckpointsManager:
    __slots__ = ("__token",)

    async def __aenter__(self, /) -> Literal[True]: ...
    def __enter__(self, /) -> Literal[True]: ...
    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...
    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

class _NoCheckpointsManager:
    __slots__ = ("__token",)

    async def __aenter__(self, /) -> Literal[False]: ...
    def __enter__(self, /) -> Literal[False]: ...
    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...
    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

@overload
def enable_checkpoints(
    wrapped: MissingType = MISSING,
    /,
) -> _CheckpointsManager: ...
@overload
def enable_checkpoints(wrapped: _AwaitableT, /) -> _AwaitableT: ...
@overload
def enable_checkpoints(wrapped: _CallableT, /) -> _CallableT: ...
@overload
def disable_checkpoints(
    wrapped: MissingType = MISSING,
    /,
) -> _NoCheckpointsManager: ...
@overload
def disable_checkpoints(wrapped: _AwaitableT, /) -> _AwaitableT: ...
@overload
def disable_checkpoints(wrapped: _CallableT, /) -> _CallableT: ...
def _threading_checkpoint() -> None: ...
def _eventlet_checkpoint() -> None: ...
def _gevent_checkpoint() -> None: ...
async def _asyncio_checkpoint() -> None: ...
async def _curio_checkpoint() -> None: ...
async def _trio_checkpoint() -> None: ...
def green_checkpoint(*, force: bool = False) -> None: ...
async def async_checkpoint(*, force: bool = False) -> None: ...
async def _asyncio_checkpoint_if_cancelled() -> None: ...
async def _curio_checkpoint_if_cancelled() -> None: ...
async def _trio_checkpoint_if_cancelled() -> None: ...
def green_checkpoint_if_cancelled(*, force: bool = False) -> None: ...
async def async_checkpoint_if_cancelled(*, force: bool = False) -> None: ...
