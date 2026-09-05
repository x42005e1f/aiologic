#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import enum
import sys

from functools import wraps
from typing import TYPE_CHECKING

from ._static import lookup_static, resolve_special

if TYPE_CHECKING:
    from typing import Any, Final

if sys.version_info >= (3, 11):
    from enum import EnumType
else:
    from enum import EnumMeta as EnumType

if TYPE_CHECKING:
    if sys.version_info >= (3, 9):
        from typing import Literal
    else:
        from typing_extensions import Literal

    if sys.version_info >= (3, 11):
        from typing import Never
    else:
        from typing_extensions import Never

if sys.version_info >= (3, 11):
    from typing import final
else:
    from typing_extensions import final

_ATTRIBUTE_SUGGESTIONS_OFFERED = sys.version_info >= (3, 10)

if "_sentinel" not in globals():
    _sentinel = object()
else:
    _prevdata = globals().copy()


class _SingletonMeta(EnumType):
    @wraps(resolve_special(EnumType, "__call__"))
    def __call__(cls, /, *args, **kwargs):
        if len(cls) != 1 or args or kwargs:
            return super().__call__(*args, **kwargs)

        return super().__call__(next(iter(cls)).value)


class SingletonEnum(enum.Enum, metaclass=_SingletonMeta):
    @wraps(resolve_special(enum.Enum, "__setattr__"))
    def __setattr__(self, name, value, /):
        if name.startswith("_") and name.endswith("_"):
            super().__setattr__(name, value)
            return

        cls = type(self)
        cls_name = cls.__name__

        try:
            cls_member = lookup_static(cls, name)
        except LookupError:
            msg = f"{cls_name!r} object has no attribute {name!r}"
        else:
            descr_set = resolve_special(
                type(cls_member),
                "__set__",
                cls_member,
                default=_sentinel,
            )

            if descr_set is not _sentinel:
                descr_set(self, value)
                return

            descr_delete = lookup_static(
                type(cls_member),
                "__delete__",
                default=_sentinel,
            )

            if descr_delete is _sentinel:
                msg = f"{cls_name!r} object attribute {name!r} is read-only"
            else:
                msg = f"{cls_name!r} object attribute {name!r} has no setter"
        exc = AttributeError(msg)
        if _ATTRIBUTE_SUGGESTIONS_OFFERED:
            exc.name = None

        try:
            raise exc
        finally:
            del exc

    def __repr__(self, /) -> str:
        return f"{self.__class__.__module__}.{self._name_}"

    def __str__(self, /) -> str:
        return f"{self.__class__.__module__}.{self._name_}"


@final
class DefaultType(SingletonEnum):
    DEFAULT = "DEFAULT"

    def __init_subclass__(cls, /, **kwargs: Any) -> Never:
        bcs = __class__
        bcs_name = bcs.__name__

        msg = f"type {bcs_name!r} is not an acceptable base type"
        raise TypeError(msg)

    def __bool__(self, /) -> Literal[False]:
        return False


@final
class MissingType(SingletonEnum):
    MISSING = "MISSING"

    def __init_subclass__(cls, /, **kwargs: Any) -> Never:
        bcs = __class__
        bcs_name = bcs.__name__

        msg = f"type {bcs_name!r} is not an acceptable base type"
        raise TypeError(msg)

    def __bool__(self, /) -> Literal[False]:
        return False


DEFAULT: Final[Literal[DefaultType.DEFAULT]] = DefaultType.DEFAULT
MISSING: Final[Literal[MissingType.MISSING]] = MissingType.MISSING

if "_prevdata" in globals():
    globals().update(
        (key, value)
        for key, value in globals().pop("_prevdata").items()
        if value is not globals().get(key, object())
    )
