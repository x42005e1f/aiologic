#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from types import MappingProxyType
from typing import Any, TypeAlias, TypeGuard, TypeVar, overload

_T = TypeVar("_T")
_T1 = TypeVar("_T1")
_T2 = TypeVar("_T2")

_ClassInfo: TypeAlias = type | tuple[_ClassInfo, ...]

def getmro_static(owner: type, /) -> tuple[type, ...]: ...
def getvars_static(owner: type, /) -> MappingProxyType[str, Any]: ...
def getabsname_static(owner: type, /) -> str: ...
def getmodulename_static(owner: type, /) -> str: ...
def getqualname_static(owner: type, /) -> str: ...
def getname_static(owner: type, /) -> str: ...
def setmodulename_static(owner: type, value: str, /) -> None: ...
def setqualname_static(owner: type, value: str, /) -> None: ...
def setname_static(owner: type, value: str, /) -> None: ...
@overload
def issubclass_static(
    obj: type,
    class_or_tuple: type[_T],
    /,
) -> TypeGuard[type[_T]]: ...
@overload
def issubclass_static(obj: type, class_or_tuple: _ClassInfo, /) -> bool: ...
@overload
def isinstance_static(
    obj: object,
    class_or_tuple: type[_T],
    /,
) -> TypeGuard[_T]: ...
@overload
def isinstance_static(obj: object, class_or_tuple: _ClassInfo, /) -> bool: ...
def ismetaclass_static(obj: object, /) -> TypeGuard[type[type]]: ...
def isclass_static(obj: object, /) -> TypeGuard[type[object]]: ...
def isdatadescriptor_static(obj: object, /) -> bool: ...
def ismethoddescriptor_static(obj: object, /) -> bool: ...
@overload
def lookup_static(owner: type, name: str, /) -> Any: ...
@overload
def lookup_static(owner: type, name: str, /, default: _T) -> Any | _T: ...
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
