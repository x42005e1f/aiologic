#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import enum
import sys

from types import MemberDescriptorType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Final, NoReturn

if sys.version_info >= (3, 11):  # `EnumMeta` has been renamed to `EnumType`
    from enum import EnumType
else:
    from enum import EnumMeta as EnumType

if TYPE_CHECKING:
    if sys.version_info >= (3, 11):  # a caching bug fix
        from typing import Literal
    else:  # typing-extensions>=4.6.0
        from typing_extensions import Literal

if sys.version_info >= (3, 11):  # runtime introspection support
    from typing import final
else:  # typing-extensions>=4.1.0
    from typing_extensions import final

# We have to use the `enum` module so that type checkers can understand that
# the instance is a singleton object. Otherwise, they will not be able to
# narrow the type of a parameter that has the default value when
# `object is SINGLETON` returns `False` (see enum literal expansion, aka
# exhaustiveness checking, or the "Support for singleton types in unions"
# section in PEP 484).


class __SingletonMeta(EnumType):
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

    Unlike :class:`enum.Enum`, it prohibits setting attributes that are not
    explicitly declared (via :ref:`slots`).

    Example:
      >>> class SingletonType(SingletonEnum):
      ...     __slots__ = ('_x',)
      ...     SINGLETON = 'SINGLETON'
      >>> SINGLETON = SingletonType.SINGLETON
      >>> repr(SINGLETON) == f"{__name__}.SINGLETON"
      True
      >>> SINGLETON._x = 1  # ok
      >>> SINGLETON._y = 2
      Traceback (most recent call last):
      AttributeError: 'SingletonType' object has no attribute '_y'
    """

    def __setattr__(self, /, name: str, value: object) -> None:
        if name.startswith("_") and name.endswith("_"):  # used by `enum.Enum`
            super().__setattr__(name, value)
            return

        cls = self.__class__
        cls_qualname = cls.__qualname__

        # We allow setting attributes for user-defined slots to better match
        # expected behavior. Although this goes against the concept in a sense
        # (since data for an instance can be set at the class/module level
        # instead), it may contribute to new usage scenarios.
        if isinstance(getattr(cls, name, None), MemberDescriptorType):
            super().__setattr__(name, value)
            return

        # A singleton object should not provide mutable public state, so we
        # raise an `AttributeError` on any attempt to set an unknown attribute,
        # suppressing its hints (which would occur if we set the `name` and
        # `obj` attributes of the exception object). Note, `enum.Enum` itself
        # does not prohibit setting attributes (see python/cpython#90290)!
        msg = f"{cls_qualname!r} object has no attribute {name!r}"
        raise AttributeError(msg)

    def __repr__(self, /) -> str:
        return f"{self.__class__.__module__}.{self._name_}"

    def __str__(self, /) -> str:  # overridden by `enum.Enum`
        return f"{self.__class__.__module__}.{self._name_}"


@final
class DefaultType(SingletonEnum):
    """
    A singleton class for :data:`DEFAULT`; mimics :data:`~types.NoneType`.
    """

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
    A singleton class for :data:`MISSING`; mimics :data:`~types.NoneType`.
    """

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
