#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, NewType

if TYPE_CHECKING:
    from typing import Any, ClassVar, Never

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

    def __deepcopy__(self, memo: Any, /) -> Never:
        cls = type(self)
        cls_name = cls.__name__

        msg = f"cannot deep copy {cls_name!r} object"
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
