#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from types import FunctionType, MethodDescriptorType, WrapperDescriptorType
from typing import TYPE_CHECKING, overload

if TYPE_CHECKING:
    from types import MappingProxyType
    from typing import Any, TypeAlias, TypeGuard, TypeVar

if sys.version_info >= (3, 15):  # PEP 661
    from builtins import sentinel
else:  # typing-extensions>=4.16.0
    from typing_extensions import sentinel

if TYPE_CHECKING:
    _T = TypeVar("_T")
    _T1 = TypeVar("_T1")
    _T2 = TypeVar("_T2")

    _ClassInfo: TypeAlias = type | tuple["_ClassInfo", ...]

if "_MISSING" not in globals():
    _MISSING = sentinel("_MISSING")
if "_NOTHING" not in globals():
    _NOTHING = sentinel("_NOTHING")

_getmro_static = vars(type)["__mro__"].__get__

_pytype_getvars_static = vars(type)["__dict__"].__get__

_pytype_getmodulename_static = vars(type)["__module__"].__get__
_pytype_getqualname_static = vars(type)["__qualname__"].__get__
_pytype_getname_static = vars(type)["__name__"].__get__

_pytype_setmodulename_static = vars(type)["__module__"].__set__
_pytype_setqualname_static = vars(type)["__qualname__"].__set__
_pytype_setname_static = vars(type)["__name__"].__set__


def getmro_static(owner: type, /) -> tuple[type, ...]:
    try:
        return _getmro_static(owner)
    except TypeError:
        msg = "the first argument must be a class"
        raise TypeError(msg) from None


def getvars_static(owner: type, /) -> MappingProxyType[str, Any]:
    try:
        return _pytype_getvars_static(owner)
    except TypeError:
        msg = "the first argument must be a class"
        raise TypeError(msg) from None


def getabsname_static(owner: type, /) -> str:
    try:
        owner_modulename = _pytype_getmodulename_static(owner)
        owner_qualname = _pytype_getqualname_static(owner)
    except TypeError:
        msg = "the first argument must be a class"
        raise TypeError(msg) from None

    return f"{owner_modulename}.{owner_qualname}"


def getmodulename_static(owner: type, /) -> str:
    try:
        return _pytype_getmodulename_static(owner)
    except TypeError:
        msg = "the first argument must be a class"
        raise TypeError(msg) from None


def getqualname_static(owner: type, /) -> str:
    try:
        return _pytype_getqualname_static(owner)
    except TypeError:
        msg = "the first argument must be a class"
        raise TypeError(msg) from None


def getname_static(owner: type, /) -> str:
    try:
        return _pytype_getname_static(owner)
    except TypeError:
        msg = "the first argument must be a class"
        raise TypeError(msg) from None


def setmodulename_static(owner: type, value: str, /) -> None:
    try:
        _pytype_setmodulename_static(owner, value)
    except TypeError:
        try:
            _pytype_getmodulename_static(owner)
        except TypeError:
            msg = "the first argument must be a class"
        else:
            msg = "the second argument must be a string"
        raise TypeError(msg) from None


def setqualname_static(owner: type, value: str, /) -> None:
    try:
        _pytype_setqualname_static(owner, value)
    except TypeError:
        try:
            _pytype_getqualname_static(owner)
        except TypeError:
            msg = "the first argument must be a class"
        else:
            msg = "the second argument must be a string"
        raise TypeError(msg) from None


def setname_static(owner: type, value: str, /) -> None:
    try:
        _pytype_setname_static(owner, value)
    except TypeError:
        try:
            _pytype_getname_static(owner)
        except TypeError:
            msg = "the first argument must be a class"
        else:
            msg = "the second argument must be a string"
        raise TypeError(msg) from None


@overload
def issubclass_static(
    obj: type,
    class_or_tuple: type[_T],
    /,
) -> TypeGuard[type[_T]]: ...
@overload
def issubclass_static(obj: type, class_or_tuple: _ClassInfo, /) -> bool: ...
def issubclass_static(obj, class_or_tuple, /):
    try:
        mro = _getmro_static(obj)
    except TypeError:
        msg = "the first argument must be a class"
        raise TypeError(msg) from None

    if isclass_static(class_or_tuple):
        if obj is class_or_tuple:
            return True

        return any(base is class_or_tuple for base in mro)

    if _istuple_static(class_or_tuple):
        return any(issubclass_static(obj, info) for info in class_or_tuple)

    msg = "the second argument must be a class or a tuple of classes"
    raise TypeError(msg)


@overload
def isinstance_static(
    obj: object,
    class_or_tuple: type[_T],
    /,
) -> TypeGuard[_T]: ...
@overload
def isinstance_static(obj: object, class_or_tuple: _ClassInfo, /) -> bool: ...
def isinstance_static(obj, class_or_tuple, /):
    return issubclass_static(type(obj), class_or_tuple)


def ismetaclass_static(obj: object, /) -> TypeGuard[type[type]]:
    if obj is type:
        return True

    try:
        mro = _getmro_static(obj)
    except TypeError:  # not a class
        return False

    return any(base is type for base in mro)


def isclass_static(obj: object, /) -> TypeGuard[type[object]]:
    cls = type(obj)

    if cls is type:
        return True

    return any(base is type for base in _getmro_static(cls))


def _isstr_static(obj, /):
    cls = type(obj)

    if cls is str:
        return True

    return any(base is str for base in _getmro_static(cls))


def _istuple_static(obj, /):
    cls = type(obj)

    if cls is tuple:
        return True

    return any(base is tuple for base in _getmro_static(cls))


def isdatadescriptor_static(obj: object, /) -> bool:
    cls = type(obj)

    for base in _getmro_static(cls):
        base_vars = _pytype_getvars_static(base)

        if "__set__" in base_vars:
            return True

        if "__delete__" in base_vars:
            return True

    return False


def ismethoddescriptor_static(obj: object, /) -> bool:
    cls = type(obj)

    if (
        cls is FunctionType
        or cls is MethodDescriptorType
        or cls is WrapperDescriptorType
    ):
        return True

    return any(
        (
            base is FunctionType
            or base is MethodDescriptorType
            or base is WrapperDescriptorType
        )
        for base in _getmro_static(cls)
    )


def _lookup_static_noerror(owner, name, /):
    try:
        mro = _getmro_static(owner)
    except TypeError:
        msg = "the first argument must be a class"
        raise TypeError(msg) from None

    if not _isstr_static(name):
        msg = "the second argument must be a string"
        raise TypeError(msg)

    for base in mro:
        base_vars = _pytype_getvars_static(base)

        if name in base_vars:
            try:
                return base_vars[name]
            except KeyError:  # a race condition
                pass

    return _NOTHING


@overload
def lookup_static(owner: type, name: str, /) -> Any: ...
@overload
def lookup_static(owner: type, name: str, /, default: _T) -> Any | _T: ...
def lookup_static(owner, name, /, default=_MISSING):
    member = _lookup_static_noerror(owner, name)

    if member is _NOTHING:
        if default is _MISSING:
            raise LookupError(name)

        return default

    return member


@overload
def resolve_special(
    owner: type,
    name: str,
    instance: None = None,
    /,
) -> Any: ...
@overload
def resolve_special(
    owner: type[_T1],
    name: str,
    instance: _T1,
    /,
) -> Any: ...
@overload
def resolve_special(
    owner: type,
    name: str,
    instance: None = None,
    /,
    *,
    default: _T2,
) -> Any | _T2: ...
@overload
def resolve_special(
    owner: type[_T1],
    name: str,
    instance: _T1,
    /,
    *,
    default: _T2,
) -> Any | _T2: ...
def resolve_special(owner, name, instance=None, /, *, default=_MISSING):
    member = _lookup_static_noerror(owner, name)

    if member is _NOTHING:
        if default is _MISSING:
            raise LookupError(name)

        return default

    descr_get = _lookup_static_noerror(type(member), "__get__")

    if descr_get is _NOTHING:
        return member

    return descr_get(member, instance, owner)
