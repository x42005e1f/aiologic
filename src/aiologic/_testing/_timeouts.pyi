#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from typing import Any, TypeVar

from aiologic.meta import DEFAULT, DefaultType

from ._executors import TaskExecutor

if sys.version_info >= (3, 11):
    from typing import TypeVarTuple, Unpack, overload
else:
    from typing_extensions import TypeVarTuple, Unpack, overload

if sys.version_info >= (3, 9):
    from collections.abc import Awaitable, Callable, Coroutine
else:
    from typing import Awaitable, Callable, Coroutine

_T = TypeVar("_T")
_Ts = TypeVarTuple("_Ts")

@overload
def _threading_timeout_after(
    seconds: float,
    maybe_func: Awaitable[_T],
    /,
) -> Coroutine[Any, Any, _T]: ...
@overload
def _threading_timeout_after(
    seconds: float,
    maybe_func: Callable[[Unpack[_Ts]], _T],
    /,
    *args: Unpack[_Ts],
) -> _T: ...
@overload
def _eventlet_timeout_after(
    seconds: float,
    maybe_func: Awaitable[_T],
    /,
) -> Coroutine[Any, Any, _T]: ...
@overload
def _eventlet_timeout_after(
    seconds: float,
    maybe_func: Callable[[Unpack[_Ts]], _T],
    /,
    *args: Unpack[_Ts],
) -> _T: ...
@overload
def _gevent_timeout_after(
    seconds: float,
    maybe_func: Awaitable[_T],
    /,
) -> Coroutine[Any, Any, _T]: ...
@overload
def _gevent_timeout_after(
    seconds: float,
    maybe_func: Callable[[Unpack[_Ts]], _T],
    /,
    *args: Unpack[_Ts],
) -> _T: ...
@overload
def _asyncio_timeout_after(
    seconds: float,
    maybe_func: Awaitable[_T],
    /,
) -> Coroutine[Any, Any, _T]: ...
@overload
def _asyncio_timeout_after(
    seconds: float,
    maybe_func: Callable[[Unpack[_Ts]], _T],
    /,
    *args: Unpack[_Ts],
) -> _T: ...
@overload
def _curio_timeout_after(
    seconds: float,
    maybe_func: Awaitable[_T],
    /,
) -> Coroutine[Any, Any, _T]: ...
@overload
def _curio_timeout_after(
    seconds: float,
    maybe_func: Callable[[Unpack[_Ts]], _T],
    /,
    *args: Unpack[_Ts],
) -> _T: ...
@overload
def _trio_timeout_after(
    seconds: float,
    maybe_func: Awaitable[_T],
    /,
) -> Coroutine[Any, Any, _T]: ...
@overload
def _trio_timeout_after(
    seconds: float,
    maybe_func: Callable[[Unpack[_Ts]], _T],
    /,
    *args: Unpack[_Ts],
) -> _T: ...
@overload
def _anyio_timeout_after(
    seconds: float,
    maybe_func: Awaitable[_T],
    /,
) -> Coroutine[Any, Any, _T]: ...
@overload
def _anyio_timeout_after(
    seconds: float,
    maybe_func: Callable[[Unpack[_Ts]], _T],
    /,
    *args: Unpack[_Ts],
) -> _T: ...
@overload
def timeout_after(
    seconds: float,
    maybe_func: Awaitable[_T],
    /,
    *,
    executor: TaskExecutor | DefaultType = DEFAULT,
) -> Coroutine[Any, Any, _T]: ...
@overload
def timeout_after(
    seconds: float,
    maybe_func: Callable[[Unpack[_Ts]], _T],
    /,
    *args: Unpack[_Ts],
    executor: TaskExecutor | DefaultType = DEFAULT,
) -> _T: ...
