#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import enum

from typing import Any, Final, Literal, NoReturn, final


class __MissingMeta(enum.EnumMeta):
    __slots__ = ()

    def __call__(cls, /, value="MISSING", *args, **kwargs):
        return super().__call__(value, *args, **kwargs)


class __DefaultMeta(enum.EnumMeta):
    __slots__ = ()

    def __call__(cls, /, value="DEFAULT", *args, **kwargs):
        return super().__call__(value, *args, **kwargs)


@final
class MissingType(enum.Enum, metaclass=__MissingMeta):
    """..."""

    __slots__ = ()

    MISSING = "MISSING"

    def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn:
        bcs = MissingType
        bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

        msg = f"type '{bcs_repr}' is not an acceptable base type"
        raise TypeError(msg)

    def __setattr__(self, /, name: str, value: Any) -> None:
        if name.startswith("_") and name.endswith("_"):
            return super().__setattr__(name, value)

        cls = self.__class__
        cls_qualname = cls.__qualname__

        msg = f"{cls_qualname!r} object has no attribute {name!r}"
        raise AttributeError(msg)

    def __repr__(self, /) -> str:
        return f"{self.__class__.__module__}.MISSING"

    def __str__(self, /) -> str:
        return f"{self.__class__.__module__}.MISSING"

    def __bool__(self, /) -> Literal[False]:
        return False


@final
class DefaultType(enum.Enum, metaclass=__DefaultMeta):
    """..."""

    __slots__ = ()

    DEFAULT = "DEFAULT"

    def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn:
        bcs = DefaultType
        bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

        msg = f"type '{bcs_repr}' is not an acceptable base type"
        raise TypeError(msg)

    def __setattr__(self, /, name: str, value: Any) -> None:
        if name.startswith("_") and name.endswith("_"):
            return super().__setattr__(name, value)

        cls = self.__class__
        cls_qualname = cls.__qualname__

        msg = f"{cls_qualname!r} object has no attribute {name!r}"
        raise AttributeError(msg)

    def __repr__(self, /) -> str:
        return f"{self.__class__.__module__}.DEFAULT"

    def __str__(self, /) -> str:
        return f"{self.__class__.__module__}.DEFAULT"

    def __bool__(self, /) -> Literal[False]:
        return False


MISSING: Final[Literal[MissingType.MISSING]] = MissingType.MISSING
DEFAULT: Final[Literal[DefaultType.DEFAULT]] = DefaultType.DEFAULT
