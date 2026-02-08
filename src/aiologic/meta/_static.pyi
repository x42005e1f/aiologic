#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from typing import Any, TypeVar

if sys.version_info >= (3, 10):  # PEP 613
    from typing import TypeAlias
else:  # typing-extensions>=3.10.0
    from typing_extensions import TypeAlias

if sys.version_info >= (3, 11):  # python/cpython#31716: introspectable
    from typing import overload
else:  # typing-extensions>=4.2.0
    from typing_extensions import overload

_T = TypeVar("_T")
_T1 = TypeVar("_T1")
_T2 = TypeVar("_T2")

_ClassInfo: TypeAlias = type | tuple[_ClassInfo, ...]

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
def isdatadescriptor_static(obj: object, /) -> bool: ...
def ismethoddescriptor_static(obj: object, /) -> bool: ...
def ismetaclass_static(obj: object, /) -> bool: ...
def isclass_static(obj: object, /) -> bool: ...
def issubclass_static(obj: object, class_or_tuple: _ClassInfo, /) -> bool: ...
def isinstance_static(obj: object, class_or_tuple: _ClassInfo, /) -> bool: ...
