#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from functools import partial, partialmethod
from types import FunctionType, MethodType, MethodWrapperType
from typing import TYPE_CHECKING

from ._static import (
    isclass_static,
    isinstance_static,
    ismetaclass_static,
    lookup_static,
    resolve_special,
)

if TYPE_CHECKING:
    if sys.version_info >= (3, 9):  # PEP 585
        from collections.abc import Iterator
    else:
        from typing import Iterator

_TYPE_CALL = lookup_static(type, "__call__")
_TYPE_NEW = lookup_static(type, "__new__")
_OBJECT_NEW = lookup_static(object, "__new__")

if sys.version_info >= (3, 13):  # python/cpython#16600
    _PARTIALMETHOD_ATTRIBUTE_NAME = "__partialmethod__"
else:
    _PARTIALMETHOD_ATTRIBUTE_NAME = "_partialmethod"

_sentinel = object()


def _iscallwrapper(obj, /):
    return (
        isinstance_static(obj, MethodWrapperType)
        and obj.__name__ == "__call__"
        and (
            not isinstance_static(obj, MethodType)  # CPython
            or obj.__func__ is FunctionType.__call__  # PyPy
        )
    )


def getsro(obj: object, /) -> Iterator[tuple[object, object | None, str]]:
    """..."""

    extra = None
    source = ""

    while True:
        yield (obj, extra, source)

        if not callable(obj):
            break

        if isclass_static(obj):
            call = lookup_static(type(obj), "__call__", _TYPE_CALL)

            if call is not _TYPE_CALL:
                try:
                    get = lookup_static(type(call), "__get__")
                except LookupError:
                    pass
                else:
                    call = get(call, obj, type(obj))

                obj = call
                extra = None
                source = "mcs.__call__"
                continue

            if ismetaclass_static(obj):
                original_new = _TYPE_NEW
            else:
                original_new = _OBJECT_NEW

            new = lookup_static(obj, "__new__", original_new)

            if new is not original_new:
                try:
                    get = lookup_static(type(new), "__get__")
                except LookupError:
                    pass
                else:
                    new = get(new, None, obj)

                obj = new
                extra = None
                source = "cls.__new__"
                continue

            # When neither `mcs.__call__()` nor `cls.__new__()` is redefined,
            # the class signature is also affected by the `cls.__init__()`
            # method. However, the latter is resolved on behalf of the
            # instance, which makes its reliable analysis on behalf of the
            # class extremely difficult: the `cls.__init__.__get__()` call
            # always precedes the `cls.__init__.__call__()` call, and it is
            # practically impossible to distinguish a user-defined callable
            # descriptor from an arbitrary function (since functions also
            # provide the `__get__()` method, and its implementation differs
            # for different types of functions).

            break
        else:
            if isinstance_static(obj, MethodType):
                obj = obj.__func__
                extra = None
                source = "method"
                continue

            if isinstance_static(obj, partial):
                obj = obj.func
                extra = None
                source = "partial"
                continue

            impl = getattr(obj, _PARTIALMETHOD_ATTRIBUTE_NAME, None)

            if isinstance_static(impl, partialmethod):
                obj = impl.func
                extra = impl
                source = "partialmethod"
                continue

            call = resolve_special(
                type(obj),
                "__call__",
                obj,
                default=_sentinel,
            )

            if call is _sentinel:
                break

            if _iscallwrapper(call) and call.__self__ is obj:
                break

            obj = call
            extra = None
            source = "obj.__call__"
            continue
