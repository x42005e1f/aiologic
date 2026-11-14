#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from typing import TYPE_CHECKING, overload

if TYPE_CHECKING:
    from types import MappingProxyType
    from typing import Any, Literal, TypeAlias, TypeGuard, TypeVar

if sys.version_info >= (3, 15):  # PEP 661
    from builtins import sentinel
else:  # typing-extensions>=4.16.0
    from typing_extensions import sentinel

if TYPE_CHECKING:
    _T = TypeVar("_T")
    _D = TypeVar("_D")

    _ClassInfo: TypeAlias = type | tuple["_ClassInfo", ...]

if "_MISSING" not in globals():
    _MISSING = sentinel("_MISSING")
if "_NOTHING" not in globals():
    _NOTHING = sentinel("_NOTHING")

_pytype_getmro_static = vars(type)["__mro__"].__get__
_pytype_getvars_static = vars(type)["__dict__"].__get__
_pytype_getmodulename_static = vars(type)["__module__"].__get__
_pytype_getqualname_static = vars(type)["__qualname__"].__get__
_pytype_getname_static = vars(type)["__name__"].__get__

_pytype_setmodulename_static = vars(type)["__module__"].__set__
_pytype_setqualname_static = vars(type)["__qualname__"].__set__
_pytype_setname_static = vars(type)["__name__"].__set__

_pytype_repr_static = type.__repr__
_pystr_ensurestr_static = str.__str__  # subclass of `str` -> `str`
_pystr_prependdot_static = ".".__add__


def getmro_static(owner: type, /) -> tuple[type, ...]:
    try:
        return _pytype_getmro_static(owner)
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
        owner_repr = _pytype_repr_static(owner)
    except TypeError:
        msg = "the first argument must be a class"
        raise TypeError(msg) from None

    # As a general rule, we should not rely on specific formatting behavior,
    # but we have to do so here to account for edge cases (such as the one
    # described below), and this is also one of the most efficient
    # implementations (excluding the asserts).
    assert owner_repr.startswith("<class '")
    assert owner_repr.endswith("'>")
    return owner_repr[8:-2]


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
def getmodulename_static(owner, /, *, ensure_str=True):
    try:
        owner_modulename = _pytype_getmodulename_static(owner)
    except TypeError:
        msg = "the first argument must be a class"
        raise TypeError(msg) from None
    except AttributeError:  # python/cpython#120857
        pass
    else:
        if ensure_str:
            try:
                return _pystr_ensurestr_static(owner_modulename)
            except TypeError:
                pass
        else:
            return owner_modulename

    # Cython uses a trick to provide module names via descriptors: a class
    # member resolves access to the object's attribute, while a metaclass
    # member resolves access to the class's attribute, and thus neither of them
    # is actually a string statically. The only reason why the class (and
    # metaclass) representation contains the module name rather than just the
    # qualified name is that the fully qualified name is set as
    # `PyTypeObject.tp_name`, and it is this value that is used by the
    # `type.__repr__()` implementation (ignoring the qualified name) when
    # `__module__` is not a string. So, to support cythonized functions and
    # similar types, we have to extract the module name from the representation
    # (since there is no direct way to get that value in pure Python, and we
    # must not trigger unknown descriptors).
    owner_absname = getabsname_static(owner)
    suffix = _pystr_prependdot_static(_pytype_getqualname_static(owner))
    if owner_absname.endswith(suffix):
        return owner_absname[: -len(suffix)]

    return None


def getqualname_static(owner: type, /, *, ensure_str: bool = True) -> str:
    try:
        owner_qualname = _pytype_getqualname_static(owner)
    except TypeError:
        msg = "the first argument must be a class"
        raise TypeError(msg) from None

    if ensure_str:
        return _pystr_ensurestr_static(owner_qualname)

    return owner_qualname


def getname_static(owner: type, /, *, ensure_str: bool = True) -> str:
    try:
        owner_name = _pytype_getname_static(owner)
    except TypeError:
        msg = "the first argument must be a class"
        raise TypeError(msg) from None

    if ensure_str:
        return _pystr_ensurestr_static(owner_name)

    return owner_name


def setmodulename_static(owner: type, value: Any, /) -> None:
    try:
        _pytype_setmodulename_static(owner, value)
    except TypeError:
        try:
            _pytype_getmodulename_static(owner)
        except TypeError:
            msg = "the first argument must be a class"
        else:
            raise  # an immutable type or something else
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
            try:
                _pystr_ensurestr_static(value)
            except TypeError:
                msg = "the second argument must be a string"
            else:
                raise  # an immutable type or something else
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
            try:
                _pystr_ensurestr_static(value)
            except TypeError:
                msg = "the second argument must be a string"
            else:
                raise  # an immutable type or something else
        raise TypeError(msg) from None


def ensurestr_static(obj: str, /) -> str:
    try:
        return _pystr_ensurestr_static(obj)
    except TypeError:
        msg = "the first argument is not a string"
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
    if isinstance(class_or_tuple, type):
        if obj is class_or_tuple:
            return True

        try:
            mro = _pytype_getmro_static(obj)
        except TypeError:
            msg = "the first argument must be a class"
            raise TypeError(msg) from None

        return any(base is class_or_tuple for base in mro)

    if isinstance(class_or_tuple, tuple):
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


def _lookup_static_noerror(owner, name, /):
    try:
        mro = _pytype_getmro_static(owner)
    except TypeError:
        msg = "the first argument must be a class"
        raise TypeError(msg) from None

    try:
        name = _pystr_ensurestr_static(name)
    except TypeError:
        msg = "the second argument must be a string"
        raise TypeError(msg) from None

    for base in mro:
        base_vars = _pytype_getvars_static(base)

        if name in base_vars:
            try:
                return base_vars[name]
            except KeyError:  # a race condition
                pass

    return _NOTHING


@overload
def lookup_static(owner: type, name: str, /, *, default: _D) -> Any | _D: ...
@overload
def lookup_static(owner: type, name: str, /) -> Any: ...
def lookup_static(owner, name, /, *, default=_MISSING):
    member = _lookup_static_noerror(owner, name)
    if member is _NOTHING:
        if default is _MISSING:
            raise LookupError(name)

        return default

    return member


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
def resolve_special(owner, name, /, instance=None, *, default=_MISSING):
    member = _lookup_static_noerror(owner, name)
    if member is _NOTHING:
        if default is _MISSING:
            raise LookupError(name)

        return default

    descr_get = _lookup_static_noerror(type(member), "__get__")
    if descr_get is _NOTHING:
        return member

    return descr_get(member, instance, owner)
