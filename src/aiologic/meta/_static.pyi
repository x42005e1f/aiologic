#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from types import MappingProxyType
from typing import Any, Literal, TypeAlias, TypeGuard, TypeVar, overload

_T = TypeVar("_T")
_D = TypeVar("_D")

_ClassInfo: TypeAlias = type | tuple[_ClassInfo, ...]

def getmro_static(owner: type, /) -> tuple[type, ...]: ...
def getvars_static(owner: type, /) -> MappingProxyType[str, Any]: ...
def getabsname_static(owner: type, /) -> str: ...
@overload
def getmodulename_static(
    owner: type,
    /,
    *,
    ensure_str: Literal[False],
) -> Any | None: ...
@overload
def getmodulename_static(
    owner: type,
    /,
    *,
    ensure_str: Literal[True] = True,
) -> str | None: ...
def getqualname_static(owner: type, /, *, ensure_str: bool = True) -> str: ...
def getname_static(owner: type, /, *, ensure_str: bool = True) -> str: ...
def setmodulename_static(owner: type, value: Any, /) -> None: ...
def setqualname_static(owner: type, value: str, /) -> None: ...
def setname_static(owner: type, value: str, /) -> None: ...
def ensurestr_static(obj: str, /) -> str: ...
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
@overload
def lookup_static(owner: type, name: str, /, *, default: _D) -> Any | _D: ...
@overload
def lookup_static(owner: type, name: str, /) -> Any: ...
@overload
def resolve_special(
    owner: type[_T],
    name: str,
    /,
    instance: _T,
    *,
    default: _D,
) -> Any | _D: ...
@overload
def resolve_special(
    owner: type,
    name: str,
    /,
    instance: None = None,
    *,
    default: _D,
) -> Any | _D: ...
@overload
def resolve_special(
    owner: type[_T],
    name: str,
    /,
    instance: _T,
) -> Any: ...
@overload
def resolve_special(
    owner: type,
    name: str,
    /,
    instance: None = None,
) -> Any: ...
