#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from typing import Any, TypeVar, overload

if sys.version_info >= (3, 9):
    from collections.abc import Awaitable, Callable
else:
    from typing import Awaitable, Callable

_AwaitableT = TypeVar("_AwaitableT", bound=Awaitable[Any])
_CallableT = TypeVar("_CallableT", bound=Callable[..., Any])

@overload
def shield(wrapped: _AwaitableT, /) -> _AwaitableT: ...
@overload
def shield(wrapped: _CallableT, /) -> _CallableT: ...
