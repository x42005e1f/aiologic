#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from typing import Any, TypeVar

from aiologic.meta import DEFAULT, DefaultType

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
def run(
    func: Awaitable[_T],
    /,
    *,
    library: str | DefaultType = DEFAULT,
    backend: str | DefaultType = DEFAULT,
    backend_options: dict[str, Any] | None = None,
) -> _T: ...
@overload
def run(
    func: Callable[[Unpack[_Ts]], Coroutine[Any, Any, _T]],
    /,
    *args: Unpack[_Ts],
    library: str | DefaultType = DEFAULT,
    backend: str | DefaultType = DEFAULT,
    backend_options: dict[str, Any] | None = None,
) -> _T: ...
@overload
def run(
    func: Callable[[Unpack[_Ts]], _T],
    /,
    *args: Unpack[_Ts],
    library: str | DefaultType = DEFAULT,
    backend: str | DefaultType = DEFAULT,
    backend_options: dict[str, Any] | None = None,
) -> _T: ...
