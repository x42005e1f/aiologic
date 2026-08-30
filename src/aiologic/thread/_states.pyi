#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from abc import ABC
from typing import Any, ClassVar

if sys.version_info >= (3, 11):  # python/cpython#30842
    from typing import Never
else:  # typing-extensions>=4.1.0
    from typing_extensions import Never

if sys.version_info >= (3, 10):  # python/cpython#27250: callable class
    from typing import NewType
else:  # typing-extensions>=4.6.0
    from typing_extensions import NewType

if sys.version_info >= (3, 11):  # python/cpython#30530: introspectable
    from typing import final
else:  # typing-extensions>=4.1.0
    from typing_extensions import final

StateReferenceKey = NewType("StateReferenceKey", object)

class BaseState(ABC):
    __slots__ = (
        "__references",
        "__weakref__",
    )

    def __init__(self, /) -> None: ...
    def __reduce__(self, /) -> Never: ...
    def __copy__(self, /) -> Never: ...
    __hash__: ClassVar[None] = None  # type: ignore[assignment]
    def add_reference(self, obj: Any, /) -> StateReferenceKey: ...
    def pop_reference(self, key: StateReferenceKey, /) -> Any: ...

@final
class ThreadState(BaseState):
    __slots__ = ()

    def __init_subclass__(cls, /, **kwargs: Any) -> Never: ...
