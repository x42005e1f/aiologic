#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from typing import Any

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if sys.version_info >= (3, 9):
    from collections.abc import Generator
else:
    from typing import Generator

class Event:
    def __new__(cls, /, is_set: bool = False) -> Self: ...
    def __bool__(self, /) -> bool: ...
    def __await__(self, /) -> Generator[Any, Any, bool]: ...
    def wait(self, /, timeout: float | None = None) -> bool: ...
    def set(self, /) -> None: ...
    def is_set(self, /) -> bool: ...
    @property
    def waiting(self, /) -> int: ...

class REvent:
    def __new__(cls, /, is_set: bool = False) -> Self: ...
    def __bool__(self, /) -> bool: ...
    def __await__(self, /) -> Generator[Any, Any, bool]: ...
    def wait(self, /, timeout: float | None = None) -> bool: ...
    def clear(self, /) -> None: ...
    def set(self, /) -> None: ...
    def is_set(self, /) -> bool: ...
    @property
    def waiting(self, /) -> int: ...

class CountdownEvent:
    def __new__(cls, /, value: int | None = None) -> Self: ...
    def __bool__(self, /) -> bool: ...
    def __await__(self, /) -> Generator[Any, Any, bool]: ...
    def wait(self, /, timeout: float | None = None) -> bool: ...
    def up(self, /, count: int = 1) -> None: ...
    def down(self, /) -> None: ...
    def clear(self, /) -> None: ...
    @property
    def waiting(self, /) -> bool: ...
    @property
    def value(self, /) -> int: ...
