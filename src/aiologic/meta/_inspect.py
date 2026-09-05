#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys
import warnings

from dataclasses import dataclass, field
from inspect import (
    CO_ASYNC_GENERATOR,
    CO_COROUTINE,
    CO_GENERATOR,
    CO_ITERABLE_COROUTINE,
    isawaitable,
    isclass,
    ismethod,
)
from types import AsyncGeneratorType, CoroutineType, GeneratorType
from typing import TYPE_CHECKING

from ._markers import MISSING
from ._signatures import getsro

if TYPE_CHECKING:
    from typing import Any, TypeVar

    from ._markers import MissingType

if sys.version_info >= (3, 9):
    from collections.abc import AsyncGenerator, Coroutine, Generator
else:
    from typing import AsyncGenerator, Coroutine, Generator

if TYPE_CHECKING:
    if sys.version_info >= (3, 9):
        from collections.abc import Awaitable, Callable
    else:
        from typing import Awaitable, Callable

if sys.version_info >= (3, 10):
    from types import NoneType
else:
    NoneType = type(None)

if TYPE_CHECKING:
    if sys.version_info >= (3, 10):
        from typing import ParamSpec
    else:
        from typing_extensions import ParamSpec

    if sys.version_info >= (3, 10):
        from typing import TypeGuard
    else:
        from typing_extensions import TypeGuard

    if sys.version_info >= (3, 13):
        from typing import TypeIs
    else:
        from typing_extensions import TypeIs

if sys.version_info >= (3, 11):
    from typing import overload
else:
    from typing_extensions import overload

if TYPE_CHECKING:
    _T = TypeVar("_T")
    _CallableT = TypeVar("_CallableT", bound=Callable[..., Any])
    _P = ParamSpec("_P")

_generator_types: tuple[type, ...] = (GeneratorType, Generator)
_coroutine_types: tuple[type, ...] = (CoroutineType, Coroutine)
_asyncgen_types: tuple[type, ...] = (AsyncGeneratorType, AsyncGenerator)


def isgeneratorlike(obj: object, /) -> TypeIs[Generator[Any, Any, Any]]:
    return isinstance(obj, _generator_types)


def iscoroutinelike(obj: object, /) -> TypeIs[Coroutine[Any, Any, Any]]:
    return isinstance(obj, _coroutine_types) or (
        isawaitable(obj) and isgeneratorlike(obj)
    )


def isasyncgenlike(obj: object, /) -> TypeIs[AsyncGenerator[Any, Any]]:
    return isinstance(obj, _asyncgen_types)


if "_prefix" not in globals():
    _prefix: str = f"_{__name__.replace(*'._')}"
else:
    _prevdata = globals().copy()


@dataclass
class _MarkerInfo:
    name: str
    value: object | MissingType = MISSING
    default: object = field(default_factory=object)


_generatorfactory_marker: _MarkerInfo = _MarkerInfo(
    f"{_prefix}_generatorfactory_marker",
)
_coroutinefactory_marker: _MarkerInfo = _MarkerInfo(
    f"{_prefix}_coroutinefactory_marker",
)
_asyncgenfactory_marker: _MarkerInfo = _MarkerInfo(
    f"{_prefix}_asyncgenfactory_marker",
)

if "_prevdata" in globals():
    globals().update(
        (key, value)
        for key, value in globals().pop("_prevdata").items()
        if value is not globals().get(key, object())
    )


def _get_generatorfactory_marker() -> _MarkerInfo:
    return _generatorfactory_marker


def _get_coroutinefactory_marker() -> _MarkerInfo:
    return _coroutinefactory_marker


def _get_asyncgenfactory_marker() -> _MarkerInfo:
    return _asyncgenfactory_marker


def _catch_generatorfactory_marker() -> _MarkerInfo:
    if _generatorfactory_marker.value is MISSING:
        _generatorfactory_marker.value = _generatorfactory_marker.default

    return _generatorfactory_marker


if sys.version_info >= (3, 12):
    from inspect import markcoroutinefunction

    class _MarkerCatchingError(RuntimeError):
        pass

    class _MarkerCatcher:
        __slots__ = (
            "_name",
            "_value",
        )

        def __setattr__(self, /, name, value):
            if hasattr(self, "_value"):
                msg = "the marker has already been set"
                raise _MarkerCatchingError(msg)

            super().__setattr__("_name", name)
            super().__setattr__("_value", value)

        def __call__(self, /):
            raise NotImplementedError

        @property
        def name(self, /):
            try:
                return self._name
            except AttributeError:
                msg = "the marker has not been set"
                raise _MarkerCatchingError(msg) from None

        @property
        def value(self, /):
            try:
                return self._value
            except AttributeError:
                msg = "the marker has not been set"
                raise _MarkerCatchingError(msg) from None

    def _catch_coroutinefactory_marker() -> _MarkerInfo:
        if _coroutinefactory_marker.value is MISSING:
            try:
                catcher = _MarkerCatcher()

                markcoroutinefunction(catcher)

                _coroutinefactory_marker.name = catcher.name
                _coroutinefactory_marker.value = catcher.value
            except _MarkerCatchingError:
                warnings.warn(
                    (
                        "Unable to obtain the standard marker; manually marked"
                        " functions using standard library tools will not be"
                        " recognized; `markcoroutinefactory()` will also not"
                        " affect `inspect.iscoroutinefunction()`"
                    ),
                    RuntimeWarning,
                    stacklevel=3,
                )
                _coroutinefactory_marker.value = (
                    _coroutinefactory_marker.default
                )

        return _coroutinefactory_marker

    _get_coroutinefactory_marker = _catch_coroutinefactory_marker
else:
    from wrapt import when_imported

    def _catch_coroutinefactory_marker() -> _MarkerInfo:
        if _coroutinefactory_marker.value is MISSING:
            try:
                from asyncio.coroutines import _is_coroutine

                _coroutinefactory_marker.name = "_is_coroutine"
                _coroutinefactory_marker.value = _is_coroutine
            except ImportError:
                warnings.warn(
                    (
                        "Unable to obtain the standard marker; manually marked"
                        " functions using standard library tools will not be"
                        " recognized; `markcoroutinefactory()` will also not"
                        " affect `asyncio.iscoroutinefunction()`"
                    ),
                    RuntimeWarning,
                    stacklevel=3,
                )
                _coroutinefactory_marker.value = (
                    _coroutinefactory_marker.default
                )

        return _coroutinefactory_marker

    @when_imported("asyncio")
    def _(_):
        global _get_coroutinefactory_marker

        _get_coroutinefactory_marker = _catch_coroutinefactory_marker


def _catch_asyncgenfactory_marker() -> _MarkerInfo:
    if _asyncgenfactory_marker.value is MISSING:
        _asyncgenfactory_marker.value = _asyncgenfactory_marker.default

    return _asyncgenfactory_marker


def _unwrap_and_check(
    obj: object,
    /,
    flag: int,
    types: tuple[type, ...] | type,
    markers: list[_MarkerInfo],
) -> bool:
    for current, _, _ in getsro(obj):
        for marker in markers:
            if getattr(current, marker.name, MISSING) is marker.value:
                return True

        if not isclass(current):
            code = getattr(current, "__code__", None)

            if code is None:
                continue

            flags = getattr(code, "co_flags", None)

            if flags is None:
                continue

            return bool(flags & flag)

    if isclass(current):
        return issubclass(current, types)

    return False


@overload
def isgeneratorfactory(
    obj: Callable[..., Generator[Any, Any, Any]],
    /,
) -> bool: ...
@overload
def isgeneratorfactory(
    obj: Callable[_P, Awaitable[_T]],
    /,
) -> TypeGuard[Callable[_P, Generator[Any, Any, _T]]]: ...
@overload
def isgeneratorfactory(
    obj: Callable[_P, object],
    /,
) -> TypeGuard[Callable[_P, Generator[Any, Any, Any]]]: ...
@overload
def isgeneratorfactory(
    obj: object,
    /,
) -> TypeGuard[Callable[..., Generator[Any, Any, Any]]]: ...
def isgeneratorfactory(obj, /):
    if (marker := _get_generatorfactory_marker()).value is not MISSING:
        markers = [marker]
    else:
        markers = []

    return _unwrap_and_check(
        obj,
        CO_GENERATOR,
        _generator_types,
        markers,
    )


@overload
def iscoroutinefactory(
    obj: Callable[..., Coroutine[Any, Any, Any]],
    /,
) -> bool: ...
@overload
def iscoroutinefactory(
    obj: Callable[_P, Awaitable[_T]],
    /,
) -> TypeGuard[Callable[_P, Coroutine[Any, Any, _T]]]: ...
@overload
def iscoroutinefactory(
    obj: Callable[_P, object],
    /,
) -> TypeGuard[Callable[_P, Coroutine[Any, Any, Any]]]: ...
@overload
def iscoroutinefactory(
    obj: object,
    /,
) -> TypeGuard[Callable[..., Coroutine[Any, Any, Any]]]: ...
def iscoroutinefactory(obj, /):
    if (marker := _get_coroutinefactory_marker()).value is not MISSING:
        markers = [marker]
    else:
        markers = []

    return _unwrap_and_check(
        obj,
        CO_COROUTINE | CO_ITERABLE_COROUTINE,
        _coroutine_types,
        markers,
    )


@overload
def isasyncgenfactory(
    obj: Callable[..., AsyncGenerator[Any, Any]],
    /,
) -> bool: ...
@overload
def isasyncgenfactory(
    obj: Callable[_P, object],
    /,
) -> TypeGuard[Callable[_P, AsyncGenerator[Any, Any]]]: ...
@overload
def isasyncgenfactory(
    obj: object,
    /,
) -> TypeGuard[Callable[..., AsyncGenerator[Any, Any]]]: ...
def isasyncgenfactory(obj, /):
    if (marker := _get_asyncgenfactory_marker()).value is not MISSING:
        markers = [marker]
    else:
        markers = []

    return _unwrap_and_check(
        obj,
        CO_ASYNC_GENERATOR,
        _asyncgen_types,
        markers,
    )


def markgeneratorfactory(factory: _CallableT, /) -> _CallableT:
    if not callable(factory):
        msg = "the first argument must be callable"
        raise TypeError(msg)

    obj = factory

    while ismethod(obj):
        obj = obj.__func__

    marker = _catch_generatorfactory_marker()

    setattr(obj, marker.name, marker.value)

    return factory


def markcoroutinefactory(factory: _CallableT, /) -> _CallableT:
    if not callable(factory):
        msg = "the first argument must be callable"
        raise TypeError(msg)

    obj = factory

    while ismethod(obj):
        obj = obj.__func__

    marker = _catch_coroutinefactory_marker()

    setattr(obj, marker.name, marker.value)

    return factory


def markasyncgenfactory(factory: _CallableT, /) -> _CallableT:
    if not callable(factory):
        msg = "the first argument must be callable"
        raise TypeError(msg)

    obj = factory

    while ismethod(obj):
        obj = obj.__func__

    marker = _catch_asyncgenfactory_marker()

    setattr(obj, marker.name, marker.value)

    return factory
