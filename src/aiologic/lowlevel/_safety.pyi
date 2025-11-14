#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from contextvars import ContextVar, Token
from types import TracebackType
from typing import Any, Literal, TypeVar

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

_signal_safety_used: bool
_signal_safety_cvar: ContextVar[tuple[int, bool | None]]

def _signal_safety_reset(token: Token[tuple[int, bool | None]], /) -> None: ...
def _signal_safety_set(enabled: bool) -> Token[tuple[int, bool | None]]: ...
def signal_safety_enabled() -> bool: ...

class _SignalSafetyManager:
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

class _NoSignalSafetyManager:
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
def enable_signal_safety(
    wrapped: MissingType = MISSING,
    /,
) -> _SignalSafetyManager: ...
@overload
def enable_signal_safety(wrapped: _AwaitableT, /) -> _AwaitableT: ...
@overload
def enable_signal_safety(wrapped: _CallableT, /) -> _CallableT: ...
@overload
def disable_signal_safety(
    wrapped: MissingType = MISSING,
    /,
) -> _NoSignalSafetyManager: ...
@overload
def disable_signal_safety(wrapped: _AwaitableT, /) -> _AwaitableT: ...
@overload
def disable_signal_safety(wrapped: _CallableT, /) -> _CallableT: ...
