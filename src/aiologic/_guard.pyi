#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from types import TracebackType
from typing import Any, Final

from .meta import DEFAULT, DefaultType

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

_USE_DELATTR: Final[bool]

class BusyResourceError(RuntimeError): ...

class ResourceGuard:
    __slots__ = (
        "__weakref__",
        "_action",
        "_unlocked",
    )

    def __new__(
        cls,
        _: DefaultType = DEFAULT,
        /,
        action: str | DefaultType = DEFAULT,
    ) -> Self: ...
    def __getnewargs__(self, /) -> tuple[Any, ...]: ...
    def __getstate__(self, /) -> None: ...
    def __copy__(self, /) -> Self: ...
    def __repr__(self, /) -> str: ...
    def __bool__(self, /) -> bool: ...
    def __enter__(self, /) -> Self: ...
    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...
    @property
    def action(self, /) -> str: ...
