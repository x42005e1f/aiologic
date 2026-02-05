#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from functools import partial, partialmethod
from inspect import getattr_static, isclass, ismethod
from types import FunctionType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.version_info >= (3, 9):  # PEP 585
        from collections.abc import Iterator
    else:
        from typing import Iterator

if sys.version_info >= (3, 11):  # python/cpython#19261
    from inspect import ismethodwrapper
else:
    from types import MethodWrapperType

    def ismethodwrapper(object):
        return isinstance(object, MethodWrapperType)


_TYPE_CALL = getattr_static(type, "__call__")
_OBJECT_NEW = getattr_static(object, "__new__")

if sys.version_info >= (3, 13):  # python/cpython#16600
    _PARTIALMETHOD_ATTRIBUTE_NAME = "__partialmethod__"
else:
    _PARTIALMETHOD_ATTRIBUTE_NAME = "_partialmethod"


def _iscallwrapper(obj, /):
    return ismethodwrapper(obj) and (
        not ismethod(obj)  # CPython
        or obj.__func__ is FunctionType.__call__  # PyPy
    )


def getsro(obj: object, /) -> Iterator[tuple[object, object | None, str]]:
    """..."""

    extra = None
    source = ""

    while True:
        yield (obj, extra, source)

        if not callable(obj):
            break

        if isclass(obj):
            call = getattr_static(type(obj), "__call__", _TYPE_CALL)

            if call is not _TYPE_CALL:
                try:
                    get = getattr_static(type(call), "__get__")
                except AttributeError:
                    pass
                else:
                    call = get(call, obj, type(obj))

                obj = call
                extra = None
                source = "mcs.__call__"
                continue

            new = getattr_static(obj, "__new__", _OBJECT_NEW)

            if new is not _OBJECT_NEW:
                try:
                    get = getattr_static(type(new), "__get__")
                except AttributeError:
                    pass
                else:
                    call = get(new, None, obj)

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
            if ismethod(obj):
                obj = obj.__func__
                extra = None
                source = "method"
                continue

            if isinstance(obj, partial):
                obj = obj.func
                extra = None
                source = "partial"
                continue

            impl = getattr(obj, _PARTIALMETHOD_ATTRIBUTE_NAME, None)

            if isinstance(impl, partialmethod):
                obj = impl.func
                extra = impl
                source = "partialmethod"
                continue

            try:
                call = getattr_static(type(obj), "__call__")
            except AttributeError:
                break
            else:
                try:
                    get = getattr_static(type(call), "__get__")
                except AttributeError:
                    pass
                else:
                    call = get(call, obj, type(obj))

                if _iscallwrapper(call) and call.__self__ is obj:
                    break

                obj = call
                extra = None
                source = "obj.__call__"
                continue
