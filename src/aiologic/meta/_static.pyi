#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from typing import Any, TypeVar

if sys.version_info >= (3, 11):  # python/cpython#31716: introspectable
    from typing import overload
else:  # typing-extensions>=4.2.0
    from typing_extensions import overload

_T = TypeVar("_T")
_T1 = TypeVar("_T1")
_T2 = TypeVar("_T2")

@overload
def lookup_static(cls: type, name: str, /) -> Any: ...
@overload
def lookup_static(cls: type, name: str, default: _T, /) -> Any | _T: ...
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
def isdatadescriptor_static(obj: object, /) -> bool: ...
def ismethoddescriptor_static(obj: object, /) -> bool: ...
def ismetaclass_static(obj: object, /) -> bool: ...
def isclass_static(obj: object, /) -> bool: ...
def issubclass_static(obj: object, cls: type, /) -> bool: ...
def isinstance_static(obj: object, cls: type) -> bool: ...
