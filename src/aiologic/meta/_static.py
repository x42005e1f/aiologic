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

# Direct calls to C-level descriptors of standard types are generally expected
# to be safe, since Python-level subclasses are ABI-compatible as-is, and
# C-level subclasses typically include the object structure of the parent class
# into their own (and thus, the pointers resolve to the exact same fields). A
# well-known exception is Nuitka, whose types intentionally pretend to be
# subclasses of non-inheritable standard types since 0.7: for example,
# `Nuitka_Function_Type` sets `tp_base` to `&PyFunction_Type` during
# initialization, but `Nuitka_FunctionObject` is not ABI-compatible with
# `PyFunctionObject`; to make the object work as expected, it simply overrides
# all parent attributes and members. If you try to use a descriptor (or even a
# method) of the parent `types.FunctionType` for a compiled function object, it
# may result in an invalid address access, and either the interpreter will
# crash with a segmentation fault, or unexpected behavior will occur (a wrong
# object is returned, a weird side effect occurs, etc.). Fortunately, there are
# currently no known instances of similar hacks for metaclasses (and tuples,
# strings), so we can expect that the members below are always safe for
# correctly implemented types (but see python/cpython#84351).

_pytype_getmro_static = vars(type)["__mro__"].__get__
_pytype_getvars_static = vars(type)["__dict__"].__get__
_pytype_getmodulename_static = vars(type)["__module__"].__get__
_pytype_getqualname_static = vars(type)["__qualname__"].__get__
_pytype_getname_static = vars(type)["__name__"].__get__

_pytype_setmodulename_static = vars(type)["__module__"].__set__
_pytype_setqualname_static = vars(type)["__qualname__"].__set__
_pytype_setname_static = vars(type)["__name__"].__set__

_pytype_repr_static = type.__repr__
_pytuple_iter_static = tuple.__iter__  # subclass of `tuple` -> iter of `tuple`
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
            except TypeError:  # not a string
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
            _pytype_getmro_static(owner)
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
            _pytype_getmro_static(owner)
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
            _pytype_getmro_static(owner)
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
                member = base_vars[name]
            except KeyError:  # a race condition
                continue

            if type(member) is nonmember:
                try:
                    member_name = member.__name__
                except AttributeError:
                    pass
                else:
                    if member_name == name:
                        break

            return member

    return _NOTHING


@overload
def lookup_static(owner: type, name: str, /, *, default: _D) -> Any | _D: ...
@overload
def lookup_static(owner: type, name: str, /) -> Any: ...
def lookup_static(owner, name, /, *, default=_MISSING):
    member = _lookup_static_noerror(owner, name)
    if member is _NOTHING:
        if default is _MISSING:
            owner_name = getname_static(owner)

            msg = f"type object {owner_name!r} has no member {name!r}"
            raise LookupError(msg)

        return default

    return member


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
def resolve_special(owner, name, /, instance=None, *, default=_MISSING):
    member = _lookup_static_noerror(owner, name)
    if member is _NOTHING:
        if default is _MISSING:
            owner_name = getname_static(owner)

            msg = f"type object {owner_name!r} has no member {name!r}"
            raise LookupError(msg)

        return default

    descr_get = _lookup_static_noerror(type(member), "__get__")
    if descr_get is _NOTHING:
        return member

    return descr_get(member, instance, owner)


@overload
def issubclass_static(
    obj: type,
    class_or_tuple: type[_T],
    /,
) -> TypeGuard[type[_T]]: ...
@overload
def issubclass_static(obj: type, class_or_tuple: _ClassInfo, /) -> bool: ...
def issubclass_static(obj, class_or_tuple, /):
    try:
        mro = _pytype_getmro_static(obj)
    except TypeError:
        msg = "the first argument must be a class"
        raise TypeError(msg) from None

    # After the previous check, the first argument is guaranteed to be a class,
    # so this cannot be true for a non-class as the second argument. We could,
    # of course, place it after the check below and have it precede the `mro`
    # lookup there, but the performance difference in the tuple case is
    # negligible, and with the current implementation, the first argument is
    # checked regardless of whether the second argument yields at least one
    # class or not (unlike the standard `issubclass()`, which simply returns
    # `False` in such a case), which seems somewhat safer for the user.
    if obj is class_or_tuple:
        return True

    if type(class_or_tuple) is not tuple:  # a fast check
        try:
            _pytype_getmro_static(class_or_tuple)
        except TypeError:  # not a class
            pass
        else:
            return any(base is class_or_tuple for base in mro)

    try:
        it = _pytuple_iter_static(class_or_tuple)
    except TypeError:
        msg = "the second argument must be a class or a tuple of classes"
        raise TypeError(msg) from None

    return any(issubclass_static(obj, info) for info in it)


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


def ensurestr_static(obj: str, /) -> str:
    try:
        return _pystr_ensurestr_static(obj)
    except TypeError:
        msg = "the first argument is not a string"
        raise TypeError(msg) from None


# ruff: ignore[module-import-not-at-top-of-file]
from ._static_descr import nonmember  # a circular import
