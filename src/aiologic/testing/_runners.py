#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from inspect import iscoroutinefunction
from typing import TYPE_CHECKING, Any, TypeVar, overload

from aiologic.lowlevel._utils import _external as external

from ._executors import create_executor

if sys.version_info >= (3, 11):
    from typing import TypeVarTuple, Unpack
else:
    from typing_extensions import TypeVarTuple, Unpack

if TYPE_CHECKING:
    if sys.version_info >= (3, 9):
        from collections.abc import Callable, Coroutine
    else:
        from typing import Callable, Coroutine

_T = TypeVar("_T")
_Ts = TypeVarTuple("_Ts")


@overload
@external
def run(
    func: Callable[[Unpack[_Ts]], Coroutine[Any, Any, _T]],
    /,
    *args: Unpack[_Ts],
    library: str | None = None,
    backend: str | None = None,
    backend_options: dict[str, Any] | None = None,
) -> _T: ...
@overload
@external
def run(
    func: Callable[[Unpack[_Ts]], _T],
    /,
    *args: Unpack[_Ts],
    library: str | None = None,
    backend: str | None = None,
    backend_options: dict[str, Any] | None = None,
) -> _T: ...
def run(func, /, *args, library=None, backend=None, backend_options=None):
    if library is None:
        if backend is None:
            if iscoroutinefunction(func):
                library = backend = "asyncio"
            else:
                library = backend = "threading"
        else:
            library = backend

    with create_executor(library, backend, backend_options) as executor:
        return executor.submit(func, *args).result()
