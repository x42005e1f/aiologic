#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from collections.abc import Awaitable
from typing import Any, Callable, TypeVar, overload

_AwaitableT = TypeVar("_AwaitableT", bound=Awaitable[Any])
_CallableT = TypeVar("_CallableT", bound=Callable[..., Any])

@overload
def shield(wrapped: _AwaitableT, /) -> _AwaitableT: ...
@overload
def shield(wrapped: _CallableT, /) -> _CallableT: ...
