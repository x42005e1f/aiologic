#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from typing import TYPE_CHECKING, Any, Generic, final, overload

from ._static import (
    ensurestr_static,
    getabsname_static,
    getmro_static,
    getname_static,
    getvars_static,
    lookup_static,
    resolve_special,
)

if TYPE_CHECKING:
    from typing import ClassVar, Never

if sys.version_info >= (3, 15):  # PEP 661
    from builtins import sentinel
else:  # typing-extensions>=4.16.0
    from typing_extensions import sentinel

if sys.version_info >= (3, 13):  # PEP 696
    from typing import TypeVar
else:  # typing-extensions>=4.12.0
    from typing_extensions import TypeVar

if TYPE_CHECKING:
    _T = TypeVar("_T")
_AnyT_co = TypeVar("_AnyT_co", covariant=True, default=Any)

if "_MISSING" not in globals():
    _MISSING = sentinel("_MISSING")
if "_NOTHING" not in globals():
    _NOTHING = sentinel("_NOTHING")


@final
class nonmember:
    __slots__ = ("__name",)

    def __init_subclass__(cls, /, **kwargs: Any) -> Never:
        bcs = __class__  # an implicit closure reference
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

    __hash__: ClassVar[None] = None

    def __set_name__(self, owner: type, name: str, /) -> None:
        try:
            self.__name = ensurestr_static(name)
        except TypeError:
            msg = "the second argument must be a string"
            raise TypeError(msg) from None

    @overload
    def __get__(
        self,
        instance: None,
        owner: type,
        /,
    ) -> Any: ...
    @overload
    def __get__(
        self,
        instance: _T,
        owner: type[_T] | None = None,
        /,
    ) -> Never: ...
    def __get__(self, instance, owner=None, /):
        try:
            name = self.__name
        except AttributeError:
            cls = type(self)
            cls_name = getname_static(cls)

            msg = f"this {cls_name!r} object has no name assigned"
            raise RuntimeError(msg) from None

        if instance is None:
            # This check, which may seem redundant at first glance, prevents
            # triggering a descriptor from a non-metaclass, which is consistent
            # with the expectations for this module.
            try:
                getmro_static(owner)
            except TypeError:  # not a class
                if owner is None:
                    msg = "__get__(None, None) is invalid"  # the standard one
                else:
                    msg = "the second argument must be a class or `None`"
                raise TypeError(msg) from None

            # Attribute lookup implemented by the `__getattribute__()` magic
            # method can be schematically represented as `<data descriptor from
            # type(object)>` -> `<member from object>` -> `<member from
            # type(object)>` (where the data descriptor must also have the
            # `__get__()` method; otherwise, it is ignored in the first step).
            # In the instance case, our descriptor is at the end of this chain,
            # so we can simply raise an `AttributeError`. But in the owner
            # case, our descriptor is in the middle, and we have no way to
            # instruct `__getattribute__()` to skip us and continue to the
            # metaclass. Therefore, we have to handle the latter ourselves.
            value = resolve_special(type(owner), name, owner, default=_NOTHING)
            if value is not _NOTHING:
                return value

            obj = owner
        else:
            obj = instance

        # To adhere to the principle of least surprise, the message should
        # resemble a standard one. Note that we do not handle module objects,
        # as doing so would make the implementation too complex, and this is an
        # unlikely use case. Starting with Python 3.16, we can begin to rely on
        # autogeneration (see python/cpython#153786).
        try:
            obj_name = getname_static(obj)
        except TypeError:  # not a class
            cls_name = getname_static(type(obj))

            msg = f"{cls_name!r} object has no attribute {name!r}"
        else:
            msg = f"type object {obj_name!r} has no attribute {name!r}"
        raise AttributeError(msg, obj=obj, name=name)

    @property
    def __objclass__(self, /) -> type:
        return object

    @property
    def __name__(self, /) -> str:
        try:
            return self.__name
        except AttributeError:
            cls = type(self)
            cls_name = getname_static(cls)

            msg = f"this {cls_name!r} object has no name assigned"
            raise AttributeError(msg, name=None) from None


@final
class classonly(Generic[_AnyT_co]):
    __slots__ = (
        "__name",
        "__owner",
        "__wrapped",
    )

    @overload
    def __init__(self, wrapped: _AnyT_co, /) -> None: ...
    @overload
    def __init__(self, /) -> None: ...
    def __init__(self, wrapped=_MISSING, /):
        if wrapped is _MISSING:
            wrapped = _NOTHING

        self.__wrapped = wrapped

    def __init_subclass__(cls, /, **kwargs: Any) -> Never:
        bcs = __class__  # an implicit closure reference
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

        wrapped = self.__wrapped
        if wrapped is not _NOTHING:
            self_repr = f"{cls_absname}({wrapped!r})"
        else:
            self_repr = f"{cls_absname}()"

        return f"<{self_repr} at {id(self):#x}>"

    __hash__: ClassVar[None] = None

    def __bool__(self, /) -> bool:
        return self.__wrapped is not _NOTHING

    def __set_name__(self, owner: type, name: str, /) -> None:
        try:
            getvars_static(owner)
        except TypeError:
            msg = "the first argument must be a class"
            raise TypeError(msg) from None

        try:
            name = ensurestr_static(name)
        except TypeError:
            msg = "the second argument must be a string"
            raise TypeError(msg) from None

        wrapped = self.__wrapped
        if wrapped is not _NOTHING:
            wrapped_set_name = resolve_special(
                type(wrapped),
                "__set_name__",
                wrapped,
                default=_NOTHING,
            )
            if wrapped_set_name is not _NOTHING:
                wrapped_set_name(owner, name)

        self.__owner = owner
        self.__name = name

    @overload
    def __get__(
        self,
        instance: None,
        owner: type,
        /,
    ) -> _AnyT_co: ...
    @overload
    def __get__(
        self,
        instance: _T,
        owner: type[_T] | None = None,
        /,
    ) -> Never: ...
    def __get__(self, instance, owner=None, /):
        try:
            name = self.__name
        except AttributeError:
            cls = type(self)
            cls_name = getname_static(cls)

            msg = f"this {cls_name!r} object has no name assigned"
            raise RuntimeError(msg) from None

        if instance is None:
            # This check, which may seem redundant at first glance, prevents
            # triggering a descriptor from a non-metaclass, which is consistent
            # with the expectations for this module.
            try:
                getmro_static(owner)
            except TypeError:  # not a class
                if owner is None:
                    msg = "__get__(None, None) is invalid"  # the standard one
                else:
                    msg = "the second argument must be a class or `None`"
                raise TypeError(msg) from None

            # If the descriptor holds a constant member, we try to resolve it
            # before returning, which allows, for example, the use of
            # `classonly()` as a decorator for `classmethod()`. To improve
            # performance, we could have moved the `__get__()` method lookup
            # into the `__init__()` special method, but then we would have had
            # to ignore the fact that classes are usually mutable, and caching
            # would therefore violate user expectations.
            wrapped = self.__wrapped
            if wrapped is not _NOTHING:
                descr_get = lookup_static(
                    type(wrapped),
                    "__get__",
                    default=_NOTHING,
                )
                if descr_get is _NOTHING:
                    return wrapped

                return descr_get(wrapped, instance, owner)

            # When the descriptor does not hold a constant member, we try to
            # look for a member further down the MRO, as if we were using the
            # `super` object. Note that we use the `after` parameter rather
            # than changing the `owner` argument, since the current `owner` may
            # have been created via multiple inheritance and thus have new
            # ancestors (and in edge cases, the `type.mro()` method of the
            # metaclass, if overridden, may make the `__mro__` of subclasses
            # completely different from that of the parent, including reversing
            # the order and even having no intersection; however, in the latter
            # case, we would not have reached this member).
            value = resolve_special(
                owner,
                name,
                after=self.__owner,
                default=_NOTHING,
            )
            if value is not _NOTHING:
                return value

            # Attribute lookup implemented by the `__getattribute__()` magic
            # method can be schematically represented as `<data descriptor from
            # type(object)>` -> `<member from object>` -> `<member from
            # type(object)>` (where the data descriptor must also have the
            # `__get__()` method; otherwise, it is ignored in the first step).
            # In the instance case, our descriptor is at the end of this chain,
            # so we can simply raise an `AttributeError`. But in the owner
            # case, our descriptor is in the middle, and we have no way to
            # instruct `__getattribute__()` to skip us and continue to the
            # metaclass. Therefore, we have to handle the latter ourselves.
            value = resolve_special(type(owner), name, owner, default=_NOTHING)
            if value is not _NOTHING:
                return value

            obj = owner
        else:
            obj = instance

        # To adhere to the principle of least surprise, the message should
        # resemble a standard one. Note that we do not handle module objects,
        # as doing so would make the implementation too complex, and this is an
        # unlikely use case. Starting with Python 3.16, we can begin to rely on
        # autogeneration (see python/cpython#153786).
        try:
            obj_name = getname_static(obj)
        except TypeError:  # not a class
            cls_name = getname_static(type(obj))

            msg = f"{cls_name!r} object has no attribute {name!r}"
        else:
            msg = f"type object {obj_name!r} has no attribute {name!r}"
        raise AttributeError(msg, obj=obj, name=name)

    @property
    def __objclass__(self, /) -> type:
        try:
            return self.__owner
        except AttributeError:
            cls = type(self)
            cls_name = getname_static(cls)

            msg = f"this {cls_name!r} object has no owner assigned"
            raise AttributeError(msg, name=None) from None

    @property
    def __name__(self, /) -> str:
        try:
            return self.__name
        except AttributeError:
            cls = type(self)
            cls_name = getname_static(cls)

            msg = f"this {cls_name!r} object has no name assigned"
            raise AttributeError(msg, name=None) from None

    @property
    def __wrapped__(self, /) -> _AnyT_co:
        wrapped = self.__wrapped
        if wrapped is _NOTHING:
            cls = type(self)
            cls_name = getname_static(cls)

            msg = f"this {cls_name!r} object has no wrapped assigned"
            raise AttributeError(msg, name=None)

        return wrapped
