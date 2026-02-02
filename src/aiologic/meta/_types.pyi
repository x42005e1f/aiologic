#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from typing import Any, Final, TypeVar

if sys.version_info >= (3, 9):  # PEP 585
    from typing import Awaitable, Callable, Coroutine, Generator
else:
    from typing import Awaitable, Callable, Coroutine, Generator

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
_ReturnT = TypeVar("_ReturnT")
_SendT = TypeVar("_SendT")
_YieldT = TypeVar("_YieldT")
_P = ParamSpec("_P")

_COPY_ANNOTATIONS: Final[bool]

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
def _copy_with_flags(func: _CallableT, /, flags: int) -> _CallableT: ...
@overload
def _generator(
    func: Callable[_P, Generator[_YieldT, _SendT, _ReturnT]],
    /,
) -> Callable[_P, Generator[_YieldT, _SendT, _ReturnT]]: ...
@overload
def _generator(
    func: Callable[_P, Coroutine[_YieldT, _SendT, _ReturnT]],
    /,
) -> Callable[_P, Generator[_YieldT, _SendT, _ReturnT]]: ...
@overload
def _generator(
    func: Callable[_P, Awaitable[_T]],
    /,
) -> Callable[_P, Generator[Any, Any, _T]]: ...
@overload
def _generator(
    func: Callable[_P, object],
    /,
) -> Callable[_P, Generator[Any, Any, Any]]: ...
@overload
def _generator(
    func: object,
    /,
) -> Callable[..., Generator[Any, Any, Any]]: ...
@overload
def _coroutine(
    func: Callable[_P, Generator[_YieldT, _SendT, _ReturnT]],
    /,
) -> Callable[_P, Coroutine[_YieldT, _SendT, _ReturnT]]: ...
@overload
def _coroutine(
    func: Callable[_P, Coroutine[_YieldT, _SendT, _ReturnT]],
    /,
) -> Callable[_P, Coroutine[_YieldT, _SendT, _ReturnT]]: ...
@overload
def _coroutine(
    func: Callable[_P, Awaitable[_T]],
    /,
) -> Callable[_P, Coroutine[Any, Any, _T]]: ...
@overload
def _coroutine(
    func: Callable[_P, object],
    /,
) -> Callable[_P, Coroutine[Any, Any, Any]]: ...
@overload
def _coroutine(
    func: object,
    /,
) -> Callable[..., Coroutine[Any, Any, Any]]: ...
@overload
def generator(
    func: Callable[_P, Generator[_YieldT, _SendT, _ReturnT]],
    /,
) -> Callable[_P, Generator[_YieldT, _SendT, _ReturnT]]: ...
@overload
def generator(
    func: Callable[_P, Coroutine[_YieldT, _SendT, _ReturnT]],
    /,
) -> Callable[_P, Generator[_YieldT, _SendT, _ReturnT]]: ...
@overload
def generator(
    func: Callable[_P, Awaitable[_T]],
    /,
) -> Callable[_P, Generator[Any, Any, _T]]: ...
@overload
def generator(
    func: Callable[_P, object],
    /,
) -> Callable[_P, Generator[Any, Any, Any]]: ...
@overload
def generator(
    func: object,
    /,
) -> Callable[..., Generator[Any, Any, Any]]: ...
@overload
def coroutine(
    func: Callable[_P, Generator[_YieldT, _SendT, _ReturnT]],
    /,
) -> Callable[_P, Coroutine[_YieldT, _SendT, _ReturnT]]: ...
@overload
def coroutine(
    func: Callable[_P, Coroutine[_YieldT, _SendT, _ReturnT]],
    /,
) -> Callable[_P, Coroutine[_YieldT, _SendT, _ReturnT]]: ...
@overload
def coroutine(
    func: Callable[_P, Awaitable[_T]],
    /,
) -> Callable[_P, Coroutine[Any, Any, _T]]: ...
@overload
def coroutine(
    func: Callable[_P, object],
    /,
) -> Callable[_P, Coroutine[Any, Any, Any]]: ...
@overload
def coroutine(
    func: object,
    /,
) -> Callable[..., Coroutine[Any, Any, Any]]: ...
