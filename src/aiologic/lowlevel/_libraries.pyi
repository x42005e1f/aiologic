#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from threading import local
from typing import Final, type_check_only

class GreenLibraryNotFoundError(RuntimeError): ...
class AsyncLibraryNotFoundError(RuntimeError): ...

@type_check_only
class _NamedLocal(local):
    name: str | None = None

current_green_library_tlocal: Final[_NamedLocal]
current_async_library_tlocal: Final[_NamedLocal]

def current_green_library(*, failsafe: bool = False) -> str: ...
def current_async_library(*, failsafe: bool = False) -> str: ...
