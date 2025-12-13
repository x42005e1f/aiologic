#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from types import CoroutineType, GeneratorType
from typing import Any, Final, Generic, TypeVar

if sys.version_info >= (3, 9):  # PEP 585
    from collections.abc import (
        Awaitable,
        Callable,
        Coroutine,
        Generator,
        Iterator,
    )
else:
    from typing import (
        Awaitable,
        Callable,
        Coroutine,
        Generator,
        Iterator,
    )

if sys.version_info >= (3, 10):  # PEP 612
    from typing import ParamSpec
else:  # typing-extensions>=3.10.0
    from typing_extensions import ParamSpec

if sys.version_info >= (3, 11):  # runtime introspection support
    from typing import overload
else:  # typing-extensions>=4.2.0
    from typing_extensions import overload

_T = TypeVar("_T")
_CallableT = TypeVar("_CallableT", bound=Callable[..., Any])
_IteratorT = TypeVar("_IteratorT", bound=Iterator[Any])
_ReturnT = TypeVar("_ReturnT")
_SendT = TypeVar("_SendT")
_YieldT = TypeVar("_YieldT")
_P = ParamSpec("_P")

_USE_NATIVE_TYPES: Final[bool]

_generator_origins: tuple[type, ...]
_coroutine_origins: tuple[type, ...]
_generatortype_names: set[str]
_coroutinetype_names: set[str]
_generatortype_prefixes: tuple[str, ...]
_coroutinetype_prefixes: tuple[str, ...]

@overload
def _get_generictype_args(
    annotation: str,
    /,
    origins: tuple[type, ...] | type,
    prefixes: tuple[str, ...],
    length: int,
) -> tuple[str, ...]: ...
@overload
def _get_generictype_args(
    annotation: Any,
    /,
    origins: tuple[type, ...] | type,
    prefixes: tuple[str, ...],
    length: int,
) -> tuple[Any, ...]: ...
@overload
def _get_generatortype_args(annotation: str, /) -> tuple[str, str, str]: ...
@overload
def _get_generatortype_args(annotation: Any, /) -> tuple[Any, Any, Any]: ...
@overload
def _get_coroutinetype_args(annotation: str, /) -> tuple[str, str, str]: ...
@overload
def _get_coroutinetype_args(annotation: Any, /) -> tuple[Any, Any, Any]: ...
def _update_returntype(
    func: _CallableT,
    /,
    transform: Callable[[Any], Any],
) -> _CallableT: ...

class _AwaitableWrapper(Generic[_IteratorT]):
    __slots__ = ("__it",)

    def __init__(self, iterator: _IteratorT, /) -> None: ...
    def __await__(self) -> _IteratorT: ...

@overload
def _generator(
    func: Callable[_P, Generator[_YieldT, _SendT, _ReturnT]],
    /,
) -> Callable[_P, GeneratorType[_YieldT, _SendT, _ReturnT]]: ...
@overload
def _generator(
    func: Callable[_P, Coroutine[_YieldT, _SendT, _ReturnT]],
    /,
) -> Callable[_P, GeneratorType[_YieldT, _SendT, _ReturnT]]: ...
@overload
def _generator(
    func: Callable[_P, Awaitable[_T]],
    /,
) -> Callable[_P, GeneratorType[Any, Any, _T]]: ...
@overload
def _generator(
    func: Callable[_P, object],
    /,
) -> Callable[_P, GeneratorType[Any, Any, Any]]: ...
@overload
def _generator(
    func: object,
    /,
) -> Callable[..., GeneratorType[Any, Any, Any]]: ...
@overload
def _coroutine(
    func: Callable[_P, Generator[_YieldT, _SendT, _ReturnT]],
    /,
) -> Callable[_P, CoroutineType[_YieldT, _SendT, _ReturnT]]: ...
@overload
def _coroutine(
    func: Callable[_P, Coroutine[_YieldT, _SendT, _ReturnT]],
    /,
) -> Callable[_P, CoroutineType[_YieldT, _SendT, _ReturnT]]: ...
@overload
def _coroutine(
    func: Callable[_P, Awaitable[_T]],
    /,
) -> Callable[_P, CoroutineType[Any, Any, _T]]: ...
@overload
def _coroutine(
    func: Callable[_P, object],
    /,
) -> Callable[_P, CoroutineType[Any, Any, Any]]: ...
@overload
def _coroutine(
    func: object,
    /,
) -> Callable[..., CoroutineType[Any, Any, Any]]: ...
@overload
def generator(
    func: Callable[_P, Generator[_YieldT, _SendT, _ReturnT]],
    /,
) -> Callable[_P, GeneratorType[_YieldT, _SendT, _ReturnT]]: ...
@overload
def generator(
    func: Callable[_P, Coroutine[_YieldT, _SendT, _ReturnT]],
    /,
) -> Callable[_P, GeneratorType[_YieldT, _SendT, _ReturnT]]: ...
@overload
def generator(
    func: Callable[_P, Awaitable[_T]],
    /,
) -> Callable[_P, GeneratorType[Any, Any, _T]]: ...
@overload
def generator(
    func: Callable[_P, object],
    /,
) -> Callable[_P, GeneratorType[Any, Any, Any]]: ...
@overload
def generator(
    func: object,
    /,
) -> Callable[..., GeneratorType[Any, Any, Any]]: ...
@overload
def coroutine(
    func: Callable[_P, Generator[_YieldT, _SendT, _ReturnT]],
    /,
) -> Callable[_P, CoroutineType[_YieldT, _SendT, _ReturnT]]: ...
@overload
def coroutine(
    func: Callable[_P, Coroutine[_YieldT, _SendT, _ReturnT]],
    /,
) -> Callable[_P, CoroutineType[_YieldT, _SendT, _ReturnT]]: ...
@overload
def coroutine(
    func: Callable[_P, Awaitable[_T]],
    /,
) -> Callable[_P, CoroutineType[Any, Any, _T]]: ...
@overload
def coroutine(
    func: Callable[_P, object],
    /,
) -> Callable[_P, CoroutineType[Any, Any, Any]]: ...
@overload
def coroutine(
    func: object,
    /,
) -> Callable[..., CoroutineType[Any, Any, Any]]: ...
