#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from collections.abc import Awaitable
from contextvars import ContextVar
from typing import Callable, Final, TypeVar, overload

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

_T = TypeVar("_T")
_P = ParamSpec("_P")

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
def repeat_if_cancelled(wrapped: Awaitable[_T], /) -> Awaitable[_T]: ...
@overload
def repeat_if_cancelled(wrapped: Callable[_P, _T], /) -> Callable[_P, _T]: ...
async def cancel_shielded_checkpoint(*, force: bool = False) -> None: ...
