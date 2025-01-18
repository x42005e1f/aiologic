#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from types import TracebackType

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

class BusyResourceError(RuntimeError): ...

class ResourceGuard:
    def __new__(cls, /, action: str = "using") -> Self: ...
    def __bool__(self, /) -> bool: ...
    def __enter__(self) -> Self: ...
    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...
    @property
    def action(self, /) -> str: ...
