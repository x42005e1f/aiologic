#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from threading import local
from typing import Literal, overload

from sniffio import AsyncLibraryNotFoundError as AsyncLibraryNotFoundError
from sniffio._impl import _ThreadLocal

class GreenLibraryNotFoundError(RuntimeError): ...

class _NamedLocal(local):
    name: str | None = None

current_green_library_tlocal: _NamedLocal
current_async_library_tlocal: _ThreadLocal

def _eventlet_running() -> bool: ...
def _gevent_running() -> bool: ...
def _asyncio_running() -> bool: ...
def _curio_running() -> bool: ...
@overload
def current_green_library(*, failsafe: Literal[False] = False) -> str: ...
@overload
def current_green_library(*, failsafe: Literal[True]) -> str | None: ...
@overload
def current_async_library(*, failsafe: Literal[False] = False) -> str: ...
@overload
def current_async_library(*, failsafe: Literal[True]) -> str | None: ...
