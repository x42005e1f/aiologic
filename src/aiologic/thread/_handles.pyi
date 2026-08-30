#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from abc import ABC
from typing import Any, Generic, TypeVar

from ._states import BaseState, ThreadState

if sys.version_info >= (3, 11):  # python/cpython#30842
    from typing import Never
else:  # typing-extensions>=4.1.0
    from typing_extensions import Never

if sys.version_info >= (3, 11):  # python/cpython#30530: introspectable
    from typing import final
else:  # typing-extensions>=4.1.0
    from typing_extensions import final

_StateT_co = TypeVar("_StateT_co", bound=BaseState, covariant=True)

class BaseHandle(ABC, Generic[_StateT_co]):
    __slots__ = (
        "__ident",
        "__state_weakref",
    )

    def __init__(self, /, state: _StateT_co, ident: int) -> None: ...
    def __reduce__(self, /) -> Never: ...
    def __copy__(self, /) -> Never: ...
    @property
    def state(self, /) -> _StateT_co | None: ...
    @property
    def ident(self, /) -> int: ...

@final
class ThreadHandle(BaseHandle[ThreadState]):
    __slots__ = ()

    def __init_subclass__(cls, /, **kwargs: Any) -> Never: ...
