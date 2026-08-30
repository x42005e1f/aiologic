#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from abc import ABC
from typing import TYPE_CHECKING

if TYPE_CHECKING:
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

    def __init__(self, /) -> None:
        super().__init__()

        self.__references = {}

    def __reduce__(self, /) -> Never:
        cls = type(self)
        cls_name = cls.__name__

        msg = f"cannot pickle {cls_name!r} object"
        raise TypeError(msg)

    def __copy__(self, /) -> Never:
        cls = type(self)
        cls_name = cls.__name__

        msg = f"cannot copy {cls_name!r} object"
        raise TypeError(msg)

    __hash__: ClassVar[None] = None

    def add_reference(self, obj: Any, /) -> StateReferenceKey:
        key = object()

        self.__references[key] = obj

        return key

    def pop_reference(self, key: StateReferenceKey, /) -> Any:
        return self.__references.pop(key)


@final
class ThreadState(BaseState):
    __slots__ = ()

    def __init_subclass__(cls, /, **kwargs: Any) -> Never:
        bcs = __class__  # an implicit closure reference
        bcs_name = bcs.__name__

        msg = f"type {bcs_name!r} is not an acceptable base type"
        raise TypeError(msg)
