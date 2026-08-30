#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys
import weakref

from abc import ABC
from typing import TYPE_CHECKING, Generic, TypeVar

from ._states import BaseState, ThreadState

if TYPE_CHECKING:
    from typing import Any

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

    def __init__(self, /, state: _StateT_co, ident: int) -> None:
        super().__init__()

        self.__ident = ident
        self.__state_weakref = weakref.ref(state)

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

    @property
    def state(self, /) -> _StateT_co | None:
        return self.__state_weakref()

    @property
    def ident(self, /) -> int:
        return self.__ident


@final
class ThreadHandle(BaseHandle[ThreadState]):
    __slots__ = ()

    def __init_subclass__(cls, /, **kwargs: Any) -> Never:
        bcs = __class__  # an implicit closure reference
        bcs_name = bcs.__name__

        msg = f"type {bcs_name!r} is not an acceptable base type"
        raise TypeError(msg)
