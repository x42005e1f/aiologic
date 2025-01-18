#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from contextvars import ContextVar
from typing import Any, Callable, Final, TypeVar, overload

if sys.version_info >= (3, 11):
    from typing import TypeVarTuple, Unpack
else:
    from typing_extensions import TypeVarTuple, Unpack

_T = TypeVar("_T")
_Ts = TypeVarTuple("_Ts")

threading_checkpoints_cvar: Final[ContextVar[bool]]
eventlet_checkpoints_cvar: Final[ContextVar[bool]]
gevent_checkpoints_cvar: Final[ContextVar[bool]]
asyncio_checkpoints_cvar: Final[ContextVar[bool]]
curio_checkpoints_cvar: Final[ContextVar[bool]]
trio_checkpoints_cvar: Final[ContextVar[bool]]

def green_checkpoint(*, force: bool = False) -> None: ...
async def checkpoint(*, force: bool = False) -> None: ...
async def async_checkpoint(*, force: bool = False) -> None: ...
async def checkpoint_if_cancelled(*, force: bool = False) -> None: ...
@overload
async def repeat_if_cancelled(func: Callable[[], _T], /) -> _T: ...
@overload
async def repeat_if_cancelled(
    func: Callable[[Unpack[_Ts]], _T],
    /,
    *args: Unpack[_Ts],
) -> _T: ...
@overload
async def repeat_if_cancelled(
    func: Callable[..., _T],
    /,
    *args: Any,
    **kwargs: Any,
) -> _T: ...
async def cancel_shielded_checkpoint(*, force: bool = False) -> None: ...
