#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from collections.abc import Awaitable
from types import TracebackType
from typing import Callable, Literal, Protocol, overload, type_check_only

if sys.version_info >= (3, 13):
    from typing import TypeVar
    from warnings import deprecated
else:
    from typing_extensions import TypeVar, deprecated

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

_T = TypeVar("_T")
_T_co = TypeVar("_T_co", covariant=True)
_ExitT_co = TypeVar(
    "_ExitT_co",
    covariant=True,
    bound=bool | None,
    default=bool | None,
)
_P = ParamSpec("_P")

@type_check_only
class _MixedContextManager(Protocol[_T_co, _ExitT_co]):
    async def __aenter__(self, /) -> _T_co: ...
    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> _ExitT_co: ...
    def __enter__(self, /) -> _T_co: ...
    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> _ExitT_co: ...

def green_checkpoint_enabled() -> bool: ...
def async_checkpoint_enabled() -> bool: ...
@overload
def enable_checkpoints() -> _MixedContextManager[Literal[True], None]: ...
@overload
def enable_checkpoints(wrapped: Awaitable[_T], /) -> Awaitable[_T]: ...
@overload
def enable_checkpoints(wrapped: Callable[_P, _T], /) -> Callable[_P, _T]: ...
@overload
def disable_checkpoints() -> _MixedContextManager[Literal[False], None]: ...
@overload
def disable_checkpoints(wrapped: Awaitable[_T], /) -> Awaitable[_T]: ...
@overload
def disable_checkpoints(wrapped: Callable[_P, _T], /) -> Callable[_P, _T]: ...
def green_checkpoint(*, force: bool = False) -> None: ...
@deprecated("Use async_checkpoint() instead")
async def checkpoint(*, force: bool = False) -> None: ...
async def async_checkpoint(*, force: bool = False) -> None: ...
def green_checkpoint_if_cancelled(*, force: bool = False) -> None: ...
async def async_checkpoint_if_cancelled(*, force: bool = False) -> None: ...
