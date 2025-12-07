#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import enum
import sys

from inspect import ismemberdescriptor
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

    if sys.version_info >= (3, 11):  # python/cpython#90633
        from typing import Never
    else:  # typing-extensions>=4.1.0
        from typing_extensions import Never

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


class _SingletonMeta(EnumType):
    # Ideally, singletons should be able to inherit abstract classes and
    # protocols, but `EnumType` conflicts with `ABCMeta` (which also applies to
    # protocols, since their metaclass inherits from the latter; see
    # python/cpython#119946, python/typeshed#8998, and python/mypy#13979).
    # Below are some thoughts on this issue and the reason why `SingletonEnum`
    # does not support it.
    #
    # Suppose we have an abstract class and we want to make our `SingletonEnum`
    # subclass inherit from it. It is best to inherit explicitly to prevent
    # incomplete or incompatible interface definitions (it will be checked both
    # at runtime and by type checkers), but we cannot do this due to the
    # metaclass conflict. Well, as a workaround, we can try the `register()`
    # method (to declare inheritance at least forcibly, without checks), but at
    # the moment, type checkers cannot handle this (see python/mypy#2922 and
    # microsoft/pyright#8139).
    #
    # What about protocols? We also will not be able to perform interface
    # compliance checks due to the metaclass conflict, but our `SingletonEnum`
    # subclass will at least be considered a protocol implementation. However,
    # there are two unpleasant aspects caused by the difference in semantics
    # between abstract classes and protocols:
    #
    # 1. Any class that implements a compatible interface is considered an
    #    implementation of the protocol (duck typing). As a result, the user
    #    can use objects that do not behave as expected (remember, interfaces
    #    do not specify behavior!), which can lead to errors that type checkers
    #    cannot detect. This makes protocols a strange choice for defining a
    #    general type for some particular ones. Related:
    #    https://stackoverflow.com/q/73245011.
    # 2. Checks using `issubclass()` and `isinstance()` are only allowed for
    #    runtime protocols, and these are structural checks. Such checks are
    #    terribly slow and completely inappropriate for the use case described
    #    in the previous point.
    #
    # One solution would be to inherit our metaclass from both `EnumType` and
    # `ABCMeta`. Moreover, we could even inherit from `typing._ProtocolMeta`
    # (but this would be a rather fragile solution due to the reference to a
    # non-public class, and would also require inheriting from
    # `typing_extensions._ProtocolMeta` if necessary, which is not very
    # convenient from a type checking perspective, since python/typeshed does
    # not include non-public names in typing-extensions). In this case, we
    # would have to restore runtime checks as described in the following links:
    #
    # * https://stackoverflow.com/q/54893595
    # * https://stackoverflow.com/q/56131308
    #
    # However, there is one non-trivial problem here, and its cause is the
    # `register()` method. What if we register some class as a subclass of our
    # `SingletonEnum` subclass? Then it will pass inheritance checks, and a
    # type checker will be left with one of the following two behaviors,
    # neither of which is desirable:
    #
    # 1. Do not handle it in any way and continue to consider the single member
    #    as the only instance. As a result, the user will be able to violate
    #    the type narrowing assumption, which will lead to errors.
    # 2. Assume that every `SingletonEnum` can have any number of instances.
    #    Then we lose its original meaning, and `is` checks will no longer be
    #    sufficient.
    #
    # We cannot solve this, and that is why our metaclass inherits only from
    # `EnumType`, thereby supporting neither abstract classes nor protocols.

    # to allow `type(SINGLETON)() is SINGLETON`
    def __call__(cls, /, *args, **kwargs):
        # If more than one member (or none members) is defined, it is unknown
        # which one the user wants to receive. Also, if additional parameters
        # are passed, the action is aimed at creating a new instance rather
        # than looking up an existing one. Therefore, in such cases, we fall
        # back to the parent implementation, which will raise a `TypeError`.
        if len(cls) != 1 or args or kwargs:
            return super().__call__(*args, **kwargs)

        return super().__call__(next(iter(cls)).value)


class SingletonEnum(enum.Enum, metaclass=_SingletonMeta):
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
        if ismemberdescriptor(getattr(cls, name, None)):
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

    DEFAULT = object()

    def __init_subclass__(cls, /, **kwargs: Never) -> NoReturn:
        bcs = __class__  # an implicit closure reference
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

    MISSING = object()

    def __init_subclass__(cls, /, **kwargs: Never) -> NoReturn:
        bcs = __class__  # an implicit closure reference
        bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

        # Although enum classes with defined members cannot be subclassed in
        # any case, we make this behavior explicit for clarity.

        msg = f"type '{bcs_repr}' is not an acceptable base type"
        raise TypeError(msg)

    def __bool__(self, /) -> Literal[False]:
        return False


DEFAULT: Final[Literal[DefaultType.DEFAULT]] = DefaultType.DEFAULT
MISSING: Final[Literal[MissingType.MISSING]] = MissingType.MISSING
