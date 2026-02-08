#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from types import (
    FunctionType,
    MappingProxyType,
    MethodDescriptorType,
    WrapperDescriptorType,
)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, TypeVar, Union

    if sys.version_info >= (3, 9):  # PEP 585
        from builtins import tuple as Tuple, type as Type
    else:
        from typing import Tuple, Type

    if sys.version_info >= (3, 10):  # PEP 613
        from typing import TypeAlias
    else:  # typing-extensions>=3.10.0
        from typing_extensions import TypeAlias

if sys.version_info >= (3, 11):  # python/cpython#31716: introspectable
    from typing import overload
else:  # typing-extensions>=4.2.0
    from typing_extensions import overload

if TYPE_CHECKING:
    _T = TypeVar("_T")
    _T1 = TypeVar("_T1")
    _T2 = TypeVar("_T2")

    _ClassInfo: TypeAlias = Union[Type, Tuple["_ClassInfo", ...]]

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
_TPFLAGS_BY_CLASS_ID = MappingProxyType({
    id(int): _TPFLAGS_LONG_SUBCLASS,
    id(list): _TPFLAGS_LIST_SUBCLASS,
    id(tuple): _TPFLAGS_TUPLE_SUBCLASS,
    id(bytes): _TPFLAGS_BYTES_SUBCLASS,
    id(str): _TPFLAGS_UNICODE_SUBCLASS,
    id(dict): _TPFLAGS_DICT_SUBCLASS,
    id(BaseException): _TPFLAGS_BASE_EXC_SUBCLASS,
    id(type): _TPFLAGS_TYPE_SUBCLASS,
})

_getflags_static = type.__dict__["__flags__"].__get__
_getmro_static = type.__dict__["__mro__"].__get__
_vars_static = type.__dict__["__dict__"].__get__

_sentinel = object()


def _lookup_static_noerror(owner, name, /):
    # see python/cpython/Objects/typeobject.c#find_name_in_mro

    try:
        mro = _getmro_static(owner)
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

    return _sentinel


@overload
def lookup_static(owner: type, name: str, /) -> Any: ...
@overload
def lookup_static(owner: type, name: str, /, default: _T) -> Any | _T: ...
def lookup_static(owner, name, /, default=_sentinel):
    """..."""

    # see python/cpython/Objects/typeobject.c#find_name_in_mro

    member = _lookup_static_noerror(owner, name)

    if member is _sentinel:
        if default is _sentinel:
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
def resolve_special(owner, name, instance=None, /, *, default=_sentinel):
    """..."""

    # see python/cpython/Objects/typeobject.c#_PyObject_LookupSpecial
    # see python/cpython/Objects/typeobject.c#slotdefs
    # see python/cpython/Objects/typeobject.c#update_one_slot
    # see python/cpython/Objects/typeobject.c#slot_tp_descr_get

    member = _lookup_static_noerror(owner, name)

    if member is _sentinel:
        if default is _sentinel:
            raise LookupError(name)

        return default

    descr_get = _lookup_static_noerror(type(member), "__get__")

    if descr_get is _sentinel:
        return member

    return descr_get(member, instance, owner)


def isdatadescriptor_static(obj: object, /) -> bool:
    """..."""

    # see python/cpython/Objects/object.c#PyObject_GenericSetAttr
    # see python/cpython/Objects/typeobject.c#slotdefs
    # see python/cpython/Objects/typeobject.c#update_one_slot

    return any(
        "__set__" in (base_vars := _vars_static(base))
        or "__delete__" in base_vars
        for base in _getmro_static(type(obj))
    )


def ismethoddescriptor_static(obj: object, /) -> bool:
    """..."""

    # see PEP 590
    # see python/cpython/Objects/funcobject.c#PyFunction_Type
    # see python/cpython/Objects/descrobject.c#PyMethodDescr_Type
    # see python/cpython/Objects/descrobject.c#PyWrapperDescr_Type
    # see python/cpython/Include/object.h#PyType_HasFeature
    # see python/cpython/Include/object.h#PyObject_TypeCheck

    cls = type(obj)

    if cls is FunctionType:
        return True

    if cls is MethodDescriptorType:
        return True

    if cls is WrapperDescriptorType:
        return True

    if _getflags_static(cls) & _TPFLAGS_METHOD_DESCRIPTOR:
        return True

    if _IS_CPYTHON:
        return False

    return any(
        (
            base is FunctionType
            or base is MethodDescriptorType
            or base is WrapperDescriptorType
        )
        for base in _getmro_static(cls)
    )


def ismetaclass_static(obj: object, /) -> bool:
    """..."""

    # see python/cpython/Include/object.h#PyType_Check
    # see python/cpython/Include/object.h#PyType_HasFeature
    # see python/cpython/Objects/typeobject.c#PyType_IsSubtype

    if obj is type:
        return True

    try:
        flags = _getflags_static(obj)
    except TypeError:  # not a class
        return False

    if flags & _TPFLAGS_TYPE_SUBCLASS:
        return True

    if _IS_CPYTHON:
        return False

    return any(base is type for base in _getmro_static(obj))


def isclass_static(obj: object, /) -> bool:
    """..."""

    # see python/cpython/Include/object.h#PyType_Check
    # see python/cpython/Include/object.h#PyType_HasFeature
    # see python/cpython/Include/object.h#PyObject_TypeCheck

    cls = type(obj)

    if cls is type:
        return True

    if _getflags_static(cls) & _TPFLAGS_TYPE_SUBCLASS:
        return True

    if _IS_CPYTHON:
        return False

    return any(base is type for base in _getmro_static(cls))


def _istuple_static(obj, /):
    # see python/cpython/Include/tupleobject.h#PyTuple_Check
    # see python/cpython/Include/object.h#PyType_HasFeature
    # see python/cpython/Include/object.h#PyObject_TypeCheck

    cls = type(obj)

    if cls is tuple:
        return True

    if _getflags_static(cls) & _TPFLAGS_TUPLE_SUBCLASS:
        return True

    if _IS_CPYTHON:
        return False

    return any(base is tuple for base in _getmro_static(cls))


def issubclass_static(obj: object, class_or_tuple: _ClassInfo, /) -> bool:
    """..."""

    # see python/cpython/Include/object.h#PyType_FastSubclass
    # see python/cpython/Objects/abstract.c#PyObject_IsSubclass

    if flag := _TPFLAGS_BY_CLASS_ID.get(id(class_or_tuple), 0):
        if obj is class_or_tuple:
            return True

        try:
            flags = _getflags_static(obj)
        except TypeError:  # not a class
            return False

        if flags & flag:
            return True

        if _IS_CPYTHON:
            return False
    elif isclass_static(class_or_tuple):
        if obj is class_or_tuple:
            return True
    elif _istuple_static(class_or_tuple):
        return any(issubclass_static(obj, info) for info in class_or_tuple)
    else:
        msg = "the second argument must be a class or a tuple of classes"
        raise TypeError(msg)

    try:
        mro = _getmro_static(obj)
    except TypeError:  # not a class
        return False

    return any(base is class_or_tuple for base in mro)


def isinstance_static(obj: object, class_or_tuple: _ClassInfo, /) -> bool:
    """..."""

    # see python/cpython/Include/object.h#PyObject_TypeCheck

    return issubclass_static(type(obj), class_or_tuple)
