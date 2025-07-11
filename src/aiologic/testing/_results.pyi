#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from concurrent.futures import Future
from typing import Any, Generic, TypeVar

if sys.version_info >= (3, 9):
    from collections.abc import Generator
else:
    from typing import Generator

_T = TypeVar("_T")

class Result(Generic[_T]):
    __slots__ = ("_future",)

    def __init__(self, /, future: Future[_T]) -> None: ...
    def __repr__(self, /) -> str: ...
    def __bool__(self, /) -> bool: ...
    def __await__(self) -> Generator[Any, Any, _T]: ...
    def wait(self, timeout: float | None = None) -> _T: ...
    @property
    def future(self, /) -> Future[_T]: ...
