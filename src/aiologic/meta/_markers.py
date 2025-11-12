#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import enum

from typing import Final, Literal, NoReturn, final

# We have to use the enum module so that type checkers can understand that the
# instance is a singleton object. Otherwise, they will not be able to narrow
# the type of a parameter that has the default value when `object is SINGLETON`
# returns `False` (see enum literal expansion, aka exhaustiveness checking, or
# https://peps.python.org/pep-0484/#support-for-singleton-types-in-unions).


class __SingletonMeta(enum.EnumMeta):
    __slots__ = ()

    __DEFAULT = object()

    # to allow `type(SINGLETON)() is SINGLETON`
    def __call__(cls, /, value=__DEFAULT, *args, **kwargs):
        DEFAULT = cls.__DEFAULT

        if value is DEFAULT:
            if (member := next(iter(cls), DEFAULT)) is not DEFAULT:
                return super().__call__(member.value, *args, **kwargs)

            return super().__call__(*args, **kwargs)

        return super().__call__(value, *args, **kwargs)


class SingletonEnum(enum.Enum, metaclass=__SingletonMeta):
    """
    A base class for creating type-checker-friendly singleton classes whose
    instances will be defined at the module level.

    Unlike :class:`enum.Enum`, it prohibits setting attributes.

    Example:
      >>> class SingletonType(SingletonEnum):
      ...     SINGLETON = "SINGLETON"
      >>> SINGLETON = SingletonType.SINGLETON
      >>> repr(SINGLETON) == f"{__name__}.SINGLETON"
      True
      >>> SINGLETON.x = "y"
      Traceback (most recent call last):
      AttributeError: 'SingletonType' object has no attribute 'x'
    """

    __slots__ = ()

    def __setattr__(self, /, name: str, value: object) -> None:
        if name.startswith("_") and name.endswith("_"):  # used by `enum.Enum`
            return super().__setattr__(name, value)

        cls = self.__class__
        cls_name = cls.__qualname__

        # A singleton object should not provide mutable state, so we raise an
        # `AttributeError` on any attempt to set an attribute, suppressing its
        # hints (which would occur if we set the `name` and `obj` attributes of
        # the exception object). Note, `enum.Enum` itself does not prohibit
        # setting attributes!

        msg = f"{cls_name!r} object has no attribute {name!r}"
        raise AttributeError(msg)

    def __repr__(self, /) -> str:
        return f"{self.__class__.__module__}.{self._name_}"

    def __str__(self, /) -> str:  # overridden by `enum.Enum`
        return f"{self.__class__.__module__}.{self._name_}"


@final
class DefaultType(SingletonEnum):
    """
    A singleton class for :data:`DEFAULT`; mimics :class:`NoneType`.
    """

    __slots__ = ()

    DEFAULT = "DEFAULT"

    def __init_subclass__(cls, /, **kwargs: object) -> NoReturn:
        bcs = DefaultType
        bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

        # Although enum classes with defined members cannot be subclassed in
        # any case, we make this behavior explicit for clarity.

        msg = f"type '{bcs_repr}' is not an acceptable base type"
        raise TypeError(msg)

    def __bool__(self, /) -> Literal[False]:
        return False


@final
class MissingType(SingletonEnum):
    """
    A singleton class for :data:`MISSING`; mimics :class:`NoneType`.
    """

    __slots__ = ()

    MISSING = "MISSING"

    def __init_subclass__(cls, /, **kwargs: object) -> NoReturn:
        bcs = MissingType
        bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

        # Although enum classes with defined members cannot be subclassed in
        # any case, we make this behavior explicit for clarity.

        msg = f"type '{bcs_repr}' is not an acceptable base type"
        raise TypeError(msg)

    def __bool__(self, /) -> Literal[False]:
        return False


DEFAULT: Final[Literal[DefaultType.DEFAULT]] = DefaultType.DEFAULT
MISSING: Final[Literal[MissingType.MISSING]] = MissingType.MISSING
