#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from typing import Any, TypeVar

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
_T = TypeVar("_T")

@overload
def _eventlet_shielded_call(
    wrapped: Callable[[], _T],
    args: None,
    kwargs: None,
    /,
) -> _T: ...
@overload
def _eventlet_shielded_call(
    wrapped: Callable[..., _T],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    /,
) -> _T: ...
@overload
def _gevent_shielded_call(
    wrapped: Callable[[], _T],
    args: None,
    kwargs: None,
    /,
) -> _T: ...
@overload
def _gevent_shielded_call(
    wrapped: Callable[..., _T],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    /,
) -> _T: ...
@overload
async def _asyncio_shielded_call(
    wrapped: Awaitable[_T],
    args: None,
    kwargs: None,
    /,
) -> _T: ...
@overload
async def _asyncio_shielded_call(
    wrapped: Callable[..., Awaitable[_T]],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    /,
) -> _T: ...
@overload
async def _curio_shielded_call(
    wrapped: Awaitable[_T],
    args: None,
    kwargs: None,
    /,
) -> _T: ...
@overload
async def _curio_shielded_call(
    wrapped: Callable[..., Awaitable[_T]],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    /,
) -> _T: ...
@overload
async def _trio_shielded_call(
    wrapped: Awaitable[_T],
    args: None,
    kwargs: None,
    /,
) -> _T: ...
@overload
async def _trio_shielded_call(
    wrapped: Callable[..., Awaitable[_T]],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    /,
) -> _T: ...
@overload
def shield(wrapped: _AwaitableT, /) -> _AwaitableT: ...
@overload
def shield(wrapped: _CallableT, /) -> _CallableT: ...
