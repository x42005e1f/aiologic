#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

from typing import TYPE_CHECKING, final

from aiologic.meta import (
    SingletonEnum,
    getabsname_static,
    getname_static,
    is_nogil,
    is_notso,
)

from ._locks import create_rlock

if TYPE_CHECKING:
    from typing import Any, Final, Literal, Never


@final
class TurnstileType:
    __slots__ = (
        "__rlock",
        "__weakref__",
    )

    def __init__(self, /) -> None:
        self.__rlock = create_rlock()

    def __init_subclass__(cls, /, **kwargs: Any) -> Never:
        bcs = __class__
        bcs_name = getname_static(bcs)

        msg = f"type {bcs_name!r} is not an acceptable base type"
        raise TypeError(msg)

    def __reduce__(self, /) -> Never:
        cls = type(self)
        cls_name = getname_static(cls)

        msg = f"cannot pickle {cls_name!r} object"
        raise TypeError(msg)

    def __deepcopy__(self, memo: Any, /) -> Never:
        cls = type(self)
        cls_name = getname_static(cls)

        msg = f"cannot deep copy {cls_name!r} object"
        raise TypeError(msg)

    def __copy__(self, /) -> Never:
        cls = type(self)
        cls_name = getname_static(cls)

        msg = f"cannot copy {cls_name!r} object"
        raise TypeError(msg)

    def __repr__(self, /) -> str:
        cls = type(self)
        cls_absname = getabsname_static(cls)

        self_repr = f"{cls_absname} object"

        return f"<{self_repr} at {id(self):#x}>"

    def wait(self, /, timeout: float = -1) -> bool:
        success = self.__rlock.acquire(True, timeout)

        if success:
            self.__rlock.release()

        return success


@final
class DummyTurnstileType(SingletonEnum):
    DUMMY_TURNSTILE = "DUMMY_TURNSTILE"

    def __init_subclass__(cls, /, **kwargs: Any) -> Never:
        bcs = __class__
        bcs_name = getname_static(bcs)

        msg = f"type {bcs_name!r} is not an acceptable base type"
        raise TypeError(msg)

    def wait(self, /, timeout: float = -1) -> Literal[True]:
        return True


DUMMY_TURNSTILE: Final[Literal[DummyTurnstileType.DUMMY_TURNSTILE]] = (
    DummyTurnstileType.DUMMY_TURNSTILE
)


def create_turnstile() -> TurnstileType:
    return TurnstileType()


def create_turnstile_if_nogil() -> TurnstileType | DummyTurnstileType:
    if is_nogil():
        return TurnstileType()
    else:
        return DUMMY_TURNSTILE


def create_turnstile_if_notso() -> TurnstileType | DummyTurnstileType:
    if is_notso():
        return TurnstileType()
    else:
        return DUMMY_TURNSTILE
