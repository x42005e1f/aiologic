#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from dataclasses import dataclass, field
from typing import Any, TypeVar

from ._markers import MISSING, MissingType

if sys.version_info >= (3, 9):  # PEP 585
    from collections.abc import (
        AsyncGenerator,
        Awaitable,
        Callable,
        Coroutine,
        Generator,
    )
else:
    from typing import (
        AsyncGenerator,
        Awaitable,
        Callable,
        Coroutine,
        Generator,
    )

if sys.version_info >= (3, 10):  # PEP 612
    from typing import ParamSpec
else:  # typing-extensions>=3.10.0
    from typing_extensions import ParamSpec

if sys.version_info >= (3, 10):  # PEP 647
    from typing import TypeGuard
else:  # typing-extensions>=3.10.0
    from typing_extensions import TypeGuard

if sys.version_info >= (3, 13):  # PEP 742
    from typing import TypeIs
else:  # typing-extensions>=4.10.0
    from typing_extensions import TypeIs

if sys.version_info >= (3, 11):  # runtime introspection support
    from typing import overload
else:  # typing-extensions>=4.2.0
    from typing_extensions import overload

_T = TypeVar("_T")
_CallableT = TypeVar("_CallableT", bound=Callable[..., Any])
_P = ParamSpec("_P")

_generator_types: tuple[type, ...]
_coroutine_types: tuple[type, ...]
_asyncgen_types: tuple[type, ...]

def isgeneratorlike(obj: object, /) -> TypeIs[Generator[Any, Any, Any]]: ...
def iscoroutinelike(obj: object, /) -> TypeIs[Coroutine[Any, Any, Any]]: ...
def isasyncgenlike(obj: object, /) -> TypeIs[AsyncGenerator[Any, Any]]: ...

@dataclass
class _MarkerInfo:
    name: str
    value: object | MissingType = MISSING
    default: object = field(default_factory=object)

_prefix: str

_generatorfactory_marker: _MarkerInfo
_coroutinefactory_marker: _MarkerInfo
_asyncgenfactory_marker: _MarkerInfo

def _get_generatorfactory_marker() -> _MarkerInfo: ...
def _get_coroutinefactory_marker() -> _MarkerInfo: ...
def _get_asyncgenfactory_marker() -> _MarkerInfo: ...
def _catch_generatorfactory_marker() -> _MarkerInfo: ...
def _catch_coroutinefactory_marker() -> _MarkerInfo: ...
def _catch_asyncgenfactory_marker() -> _MarkerInfo: ...

_partialmethod_attribute_name: str

def _iscallwrapper(obj: object, /) -> bool: ...
def _unwrap_and_check(
    obj: object,
    /,
    flag: int,
    types: tuple[type, ...] | type,
    markers: list[_MarkerInfo],
) -> bool: ...
@overload
def isgeneratorfactory(  # pyright: ignore[reportOverlappingOverload]
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
@overload
def iscoroutinefactory(  # pyright: ignore[reportOverlappingOverload]
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
@overload
def isasyncgenfactory(  # pyright: ignore[reportOverlappingOverload]
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
def markgeneratorfactory(factory: _CallableT, /) -> _CallableT: ...
def markcoroutinefactory(factory: _CallableT, /) -> _CallableT: ...
def markasyncgenfactory(factory: _CallableT, /) -> _CallableT: ...
