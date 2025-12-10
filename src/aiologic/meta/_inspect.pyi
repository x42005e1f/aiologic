#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from dataclasses import dataclass, field
from types import AsyncGeneratorType, CodeType, CoroutineType, GeneratorType
from typing import Any, TypeVar, type_check_only

from ._markers import DEFAULT, MISSING, DefaultType, MissingType

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

if sys.version_info >= (3, 11):  # a caching bug fix
    from typing import Literal
else:  # typing-extensions>=4.6.0
    from typing_extensions import Literal

if sys.version_info >= (3, 10):  # PEP 612
    from typing import ParamSpec
else:  # typing-extensions>=3.10.0
    from typing_extensions import ParamSpec

if sys.version_info >= (3, 13):  # various fixes and improvements
    from typing import Protocol
else:  # typing-extensions>=4.10.0
    from typing_extensions import Protocol

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

@type_check_only
class _FunctionLike(Protocol):
    __code__: CodeType
    __name__: str
    __defaults__: tuple[Any, ...] | None
    __kwdefaults__: dict[str, Any] | None

    def __call__(self, /, *args: Any, **kwargs: Any) -> Any: ...

_T = TypeVar("_T")
_CallableT = TypeVar("_CallableT", bound=Callable[..., Any])
_P = ParamSpec("_P")

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
_generatorfunction_marker: _MarkerInfo
_coroutinefunction_marker: _MarkerInfo
_asyncgenfunction_marker: _MarkerInfo

def _get_generatorfactory_marker() -> _MarkerInfo: ...
def _get_coroutinefactory_marker() -> _MarkerInfo: ...
def _get_asyncgenfactory_marker() -> _MarkerInfo: ...
def _get_generatorfunction_marker() -> _MarkerInfo: ...
def _get_coroutinefunction_marker() -> _MarkerInfo: ...
def _get_asyncgenfunction_marker() -> _MarkerInfo: ...
def _catch_generatorfactory_marker() -> _MarkerInfo: ...
def _catch_coroutinefactory_marker() -> _MarkerInfo: ...
def _catch_asyncgenfactory_marker() -> _MarkerInfo: ...
def _catch_generatorfunction_marker() -> _MarkerInfo: ...
def _catch_coroutinefunction_marker() -> _MarkerInfo: ...
def _catch_asyncgenfunction_marker() -> _MarkerInfo: ...

_partialmethod_attribute_name: str

def _isfunctionlike(obj: object) -> TypeIs[_FunctionLike]: ...
def _unwrap_and_check(
    obj: object,
    /,
    flag: int,
    types: tuple[type, ...] | type,
    markers: list[_MarkerInfo],
) -> bool: ...
@overload
def isgeneratorfactory(
    obj: Callable[..., Generator[Any, Any, Any]],
    /,
    *,
    native: bool | DefaultType = DEFAULT,
) -> bool: ...
@overload
def isgeneratorfactory(
    obj: Callable[_P, Awaitable[_T]],
    /,
    *,
    native: Literal[True],
) -> TypeGuard[Callable[_P, GeneratorType[Any, Any, _T]]]: ...
@overload
def isgeneratorfactory(
    obj: Callable[_P, Awaitable[_T]],
    /,
    *,
    native: bool | DefaultType = DEFAULT,
) -> TypeGuard[Callable[_P, Generator[Any, Any, _T]]]: ...
@overload
def isgeneratorfactory(
    obj: Callable[_P, object],
    /,
    *,
    native: Literal[True],
) -> TypeGuard[Callable[_P, GeneratorType[Any, Any, Any]]]: ...
@overload
def isgeneratorfactory(
    obj: Callable[_P, object],
    /,
    *,
    native: bool | DefaultType = DEFAULT,
) -> TypeGuard[Callable[_P, Generator[Any, Any, Any]]]: ...
@overload
def isgeneratorfactory(
    obj: object,
    /,
    *,
    native: Literal[True],
) -> TypeGuard[Callable[..., GeneratorType[Any, Any, Any]]]: ...
@overload
def isgeneratorfactory(
    obj: object,
    /,
    *,
    native: bool | DefaultType = DEFAULT,
) -> TypeGuard[Callable[..., Generator[Any, Any, Any]]]: ...
@overload
def iscoroutinefactory(
    obj: Callable[..., Coroutine[Any, Any, Any]],
    /,
    *,
    native: bool | DefaultType = DEFAULT,
) -> bool: ...
@overload
def iscoroutinefactory(
    obj: Callable[_P, Awaitable[_T]],
    /,
    *,
    native: Literal[True],
) -> TypeGuard[Callable[_P, CoroutineType[Any, Any, _T]]]: ...
@overload
def iscoroutinefactory(
    obj: Callable[_P, Awaitable[_T]],
    /,
    *,
    native: bool | DefaultType = DEFAULT,
) -> TypeGuard[Callable[_P, Coroutine[Any, Any, _T]]]: ...
@overload
def iscoroutinefactory(
    obj: Callable[_P, object],
    /,
    *,
    native: Literal[True],
) -> TypeGuard[Callable[_P, CoroutineType[Any, Any, Any]]]: ...
@overload
def iscoroutinefactory(
    obj: Callable[_P, object],
    /,
    *,
    native: bool | DefaultType = DEFAULT,
) -> TypeGuard[Callable[_P, Coroutine[Any, Any, Any]]]: ...
@overload
def iscoroutinefactory(
    obj: object,
    /,
    *,
    native: Literal[True],
) -> TypeGuard[Callable[..., CoroutineType[Any, Any, Any]]]: ...
@overload
def iscoroutinefactory(
    obj: object,
    /,
    *,
    native: bool | DefaultType = DEFAULT,
) -> TypeGuard[Callable[..., Coroutine[Any, Any, Any]]]: ...
@overload
def isasyncgenfactory(
    obj: Callable[..., AsyncGenerator[Any, Any]],
    /,
    *,
    native: bool | DefaultType = DEFAULT,
) -> bool: ...
@overload
def isasyncgenfactory(
    obj: Callable[_P, object],
    /,
    *,
    native: Literal[True],
) -> TypeGuard[Callable[_P, AsyncGeneratorType[Any, Any]]]: ...
@overload
def isasyncgenfactory(
    obj: Callable[_P, object],
    /,
    *,
    native: bool | DefaultType = DEFAULT,
) -> TypeGuard[Callable[_P, AsyncGenerator[Any, Any]]]: ...
@overload
def isasyncgenfactory(
    obj: object,
    /,
    *,
    native: Literal[True],
) -> TypeGuard[Callable[..., AsyncGeneratorType[Any, Any]]]: ...
@overload
def isasyncgenfactory(
    obj: object,
    /,
    *,
    native: bool | DefaultType = DEFAULT,
) -> TypeGuard[Callable[..., AsyncGenerator[Any, Any]]]: ...
@overload
def markgeneratorfactory(
    factory: MissingType = MISSING,
    /,
    *,
    native: bool | DefaultType = DEFAULT,
) -> Callable[[_CallableT], _CallableT]: ...
@overload
def markgeneratorfactory(
    factory: _CallableT,
    /,
    *,
    native: bool | DefaultType = DEFAULT,
) -> _CallableT: ...
@overload
def markcoroutinefactory(
    factory: MissingType = MISSING,
    /,
    *,
    native: bool | DefaultType = DEFAULT,
) -> Callable[[_CallableT], _CallableT]: ...
@overload
def markcoroutinefactory(
    factory: _CallableT,
    /,
    *,
    native: bool | DefaultType = DEFAULT,
) -> _CallableT: ...
@overload
def markasyncgenfactory(
    factory: MissingType = MISSING,
    /,
    *,
    native: bool | DefaultType = DEFAULT,
) -> Callable[[_CallableT], _CallableT]: ...
@overload
def markasyncgenfactory(
    factory: _CallableT,
    /,
    *,
    native: bool | DefaultType = DEFAULT,
) -> _CallableT: ...
