#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from types import FunctionType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, TypeVar

if sys.version_info >= (3, 11):  # python/cpython#31716: introspectable
    from typing import overload
else:  # typing-extensions>=4.2.0
    from typing_extensions import overload

if TYPE_CHECKING:
    _T = TypeVar("_T")
    _T1 = TypeVar("_T1")
    _T2 = TypeVar("_T2")

_IS_CPYTHON = sys.implementation.name == "cpython"

# see python/cpython/Include/object.h
_TPFLAGS_METHOD_DESCRIPTOR = 1 << 17
_TPFLAGS_LONG_SUBCLASS = 1 << 24
_TPFLAGS_LIST_SUBCLASS = 1 << 25
_TPFLAGS_TUPLE_SUBCLASS = 1 << 26
_TPFLAGS_BYTES_SUBCLASS = 1 << 27
_TPFLAGS_UNICODE_SUBCLASS = 1 << 28
_TPFLAGS_DICT_SUBCLASS = 1 << 29
_TPFLAGS_BASE_EXC_SUBCLASS = 1 << 30
_TPFLAGS_TYPE_SUBCLASS = 1 << 31
_TPFLAGS_BY_TYPE = {
    int: _TPFLAGS_LONG_SUBCLASS,
    list: _TPFLAGS_LIST_SUBCLASS,
    tuple: _TPFLAGS_TUPLE_SUBCLASS,
    bytes: _TPFLAGS_BYTES_SUBCLASS,
    str: _TPFLAGS_UNICODE_SUBCLASS,
    dict: _TPFLAGS_DICT_SUBCLASS,
    BaseException: _TPFLAGS_BASE_EXC_SUBCLASS,
    type: _TPFLAGS_TYPE_SUBCLASS,
}

_getflags_static = type.__dict__["__flags__"].__get__
_getmro_static = type.__dict__["__mro__"].__get__
_vars_static = type.__dict__["__dict__"].__get__

_sentinel = object()


# see python/cpython/Object/typeobject.c#find_name_in_mro
@overload
def lookup_static(cls: type, name: str, /) -> Any: ...
@overload
def lookup_static(cls: type, name: str, default: _T, /) -> Any | _T: ...
def lookup_static(cls, name, default=_sentinel, /):
    """..."""

    try:
        mro = _getmro_static(cls)
    except TypeError:  # not a class
        msg = "the first argument must be a class"
        raise TypeError(msg) from None

    for base in mro:
        base_vars = _vars_static(base)

        if name in base_vars:
            try:
                return base_vars[name]
            except KeyError:  # a race condition
                pass

    if default is _sentinel:
        raise LookupError(name)

    return default


# see python/cpython/Object/typeobject.c#find_name_in_mro
def _lookup_static_noerror(cls, name, /):
    for base in _getmro_static(cls):
        base_vars = _vars_static(base)

        if name in base_vars:
            try:
                return base_vars[name]
            except KeyError:  # a race condition
                pass

    return _sentinel


# see python/cpython/Object/typeobject.c#_PyObject_LookupSpecial
@overload
def resolvespecial(owner: type, instance: None, name: str, /) -> Any: ...
@overload
def resolvespecial(owner: type[_T1], instance: _T1, name: str, /) -> Any: ...
@overload
def resolvespecial(
    owner: type,
    instance: None,
    name: str,
    default: _T2,
    /,
) -> Any | _T2: ...
@overload
def resolvespecial(
    owner: type[_T1],
    instance: _T1,
    name: str,
    default: _T2,
    /,
) -> Any | _T2: ...
def resolvespecial(owner, instance, name, default=_sentinel, /):
    """..."""

    try:
        meta_member = _lookup_static_noerror(owner, name)
    except TypeError:  # not a class
        msg = "the first argument must be a class"
        raise TypeError(msg) from None

    if meta_member is _sentinel:
        if default is _sentinel:
            raise LookupError(name)

        return default

    meta_get = _lookup_static_noerror(type(meta_member), "__get__")

    if meta_get is _sentinel:
        return meta_member

    return meta_get(meta_member, instance, owner)


# see python/cpython/Objects/typeobject.c#slot_tp_descr_set
def isdatadescriptor_static(obj: object, /) -> bool:
    """..."""

    for base in _getmro_static(type(obj)):
        base_vars = _vars_static(base)

        if "__set__" in base_vars or "__delete__" in base_vars:
            return True

    return False


# see PEP 590
def ismethoddescriptor_static(obj: object, /) -> bool:
    """..."""

    if _getflags_static(type(obj)) & _TPFLAGS_METHOD_DESCRIPTOR:
        return True

    if _IS_CPYTHON:
        return False

    # PyPy: `FunctionType is MethodDescriptorType is WrapperDescriptorType`
    return any(base is FunctionType for base in _getmro_static(type(obj)))


# see python/cpython/Object/typeobject.c#PyType_IsSubtype
def ismetaclass_static(obj: object, /) -> bool:
    """..."""

    try:
        flags = _getflags_static(obj)
    except TypeError:  # not a class
        return False

    if flags & _TPFLAGS_TYPE_SUBCLASS:
        return True

    if _IS_CPYTHON:
        return False

    return any(base is type for base in _getmro_static(obj))


# see python/cpython/Include/object.h#PyObject_TypeCheck
def isclass_static(obj: object, /) -> bool:
    """..."""

    if _getflags_static(type(obj)) & _TPFLAGS_TYPE_SUBCLASS:
        return True

    if _IS_CPYTHON:
        return False

    return any(base is type for base in _getmro_static(type(obj)))


# see python/cpython/Object/typeobject.c#PyType_IsSubtype
def issubclass_static(obj: object, cls: type, /) -> bool:
    """..."""

    if flag := _TPFLAGS_BY_TYPE.get(cls, 0):
        try:
            flags = _getflags_static(obj)
        except TypeError:  # not a class
            return False

        if flags & flag:
            return True

        if _IS_CPYTHON:
            return False

    try:
        mro = _getmro_static(obj)
    except TypeError:  # not a class
        return False

    return any(base is cls for base in mro)


# see python/cpython/Include/object.h#PyObject_TypeCheck
def isinstance_static(obj: object, cls: type) -> bool:
    """..."""

    if flag := _TPFLAGS_BY_TYPE.get(cls, 0):
        if _getflags_static(type(obj)) & flag:
            return True

        if _IS_CPYTHON:
            return False

    return any(base is cls for base in _getmro_static(type(obj)))
