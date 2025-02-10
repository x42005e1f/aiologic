#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from threading import Thread, local
from typing import Any, Callable, TypeVar, overload

if sys.version_info >= (3, 11):
    from typing import TypeVarTuple, Unpack
else:
    from typing_extensions import TypeVarTuple, Unpack

_T = TypeVar("_T")
_Ts = TypeVarTuple("_Ts")

def get_thread(ident: int, /) -> Thread | None: ...
def current_thread() -> Thread | None: ...
def current_thread_ident() -> int: ...
def once(func: Callable[[], _T], /) -> Callable[[], _T]: ...

ThreadLocal = local

@overload
def start_new_thread(
    target: Callable[[], object],
    *,
    daemon: bool = True,
) -> int: ...
@overload
def start_new_thread(
    target: Callable[[Unpack[_Ts]], object],
    args: tuple[Unpack[_Ts]],
    *,
    daemon: bool = True,
) -> int: ...
@overload
def start_new_thread(
    target: Callable[..., object],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    *,
    daemon: bool = True,
) -> int: ...
@overload
def start_new_thread(
    target: Callable[..., object],
    *,
    kwargs: dict[str, Any],
    daemon: bool = True,
) -> int: ...
def add_thread_finalizer(
    ident: int,
    func: Callable[[], object],
    /,
    *,
    ref: object = None,
) -> object: ...
def remove_thread_finalizer(ident: int, key: object, /) -> bool: ...
