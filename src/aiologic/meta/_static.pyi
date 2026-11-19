#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from types import MappingProxyType
from typing import (
    Any,
    ClassVar,
    Literal,
    Never,
    TypeAlias,
    TypeGuard,
    TypeVar,
    final,
    overload,
)

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
@overload
def lookup_static(owner: type, name: str, /, *, default: _D) -> Any | _D: ...
@overload
def lookup_static(owner: type, name: str, /) -> Any: ...
@overload
def resolve_special(
    owner: type[_T],
    name: str,
    /,
    instance: _T | None = None,
    *,
    default: _D,
) -> Any | _D: ...
@overload
def resolve_special(
    owner: type[_T],
    name: str,
    /,
    instance: _T | None = None,
) -> Any: ...
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
def ensurestr_static(obj: str, /) -> str: ...

@final
class nonmember:
    __slots__ = ("__name",)

    def __init__(self, /, name: str | None = None) -> None: ...
    def __init_subclass__(cls, /, **kwargs: Any) -> Never: ...
    def __reduce__(self, /) -> Never: ...
    def __deepcopy__(self, memo: Any, /) -> Never: ...
    def __copy__(self, /) -> Never: ...
    def __repr__(self, /) -> str: ...
    __hash__: ClassVar[None]  # type: ignore[assignment]
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
    def __set_name__(self, owner: type, name: str, /) -> None: ...
    @property
    def name(self, /) -> str | None: ...
