#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from collections.abc import Callable, Iterable, MutableMapping
from typing import Any, ParamSpec, TypeVar, overload

from ._markers import MISSING, MissingType

if sys.version_info >= (3, 12):
    from typing import Protocol
else:
    from typing_extensions import Protocol

_T = TypeVar("_T")
_T_co = TypeVar("_T_co", covariant=True)
_NamedCallableT = TypeVar("_NamedCallableT", bound=_NamedCallable[..., Any])
_P = ParamSpec("_P")

class _NamedCallable(Protocol[_P, _T_co]):
    def __call__(self, /, *args: _P.args, **kwargs: _P.kwargs) -> _T_co: ...
    @property
    def __name__(self, /) -> str: ...

@overload
def replaces(
    namespace: MutableMapping[str, Any],
    replacer: MissingType = MISSING,
    /,
) -> Callable[[_NamedCallableT], _NamedCallableT]: ...
@overload
def replaces(
    namespace: MutableMapping[str, Any],
    replacer: _NamedCallableT,
    /,
) -> _NamedCallableT: ...
@overload
def replaces_when_imported(
    namespace: MutableMapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    replacer: MissingType = MISSING,
    /,
) -> Callable[[_NamedCallableT], _NamedCallableT]: ...
@overload
def replaces_when_imported(
    namespace: MutableMapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    replacer: _NamedCallableT,
    /,
) -> _NamedCallableT: ...
@overload
def replaces_with_outcome(
    namespace: MutableMapping[str, Any],
    replacer: MissingType = MISSING,
    /,
) -> Callable[[_NamedCallable[[], Callable[_P, _T]]], Callable[_P, _T]]: ...
@overload
def replaces_with_outcome(
    namespace: MutableMapping[str, Any],
    replacer: _NamedCallable[[], Callable[_P, _T]],
    /,
) -> Callable[_P, _T]: ...
@overload
def copies(
    original: Callable[_P, _T],
    replaced: MissingType = MISSING,
    /,
) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]: ...
@overload
def copies(
    original: Callable[_P, _T],
    replaced: Callable[_P, _T],
    /,
) -> Callable[_P, _T]: ...
