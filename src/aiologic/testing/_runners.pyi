#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from typing import Any, TypeVar, overload

if sys.version_info >= (3, 11):
    from typing import TypeVarTuple, Unpack
else:
    from typing_extensions import TypeVarTuple, Unpack

if sys.version_info >= (3, 9):
    from collections.abc import Awaitable, Callable, Coroutine
else:
    from typing import Awaitable, Callable, Coroutine

_T = TypeVar("_T")
_Ts = TypeVarTuple("_Ts")

@overload
def run(
    func: Awaitable[_T],
    /,
    *,
    library: str | None = None,
    backend: str | None = None,
    backend_options: dict[str, Any] | None = None,
) -> _T: ...
@overload
def run(
    func: Callable[[Unpack[_Ts]], Coroutine[Any, Any, _T]],
    /,
    *args: Unpack[_Ts],
    library: str | None = None,
    backend: str | None = None,
    backend_options: dict[str, Any] | None = None,
) -> _T: ...
@overload
def run(
    func: Callable[[Unpack[_Ts]], _T],
    /,
    *args: Unpack[_Ts],
    library: str | None = None,
    backend: str | None = None,
    backend_options: dict[str, Any] | None = None,
) -> _T: ...
