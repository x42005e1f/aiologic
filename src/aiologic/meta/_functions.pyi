#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from typing import Any, TypeVar

from ._markers import MISSING, MissingType

if sys.version_info >= (3, 9):  # PEP 585
    from collections.abc import Callable, MutableMapping
else:
    from typing import Callable, MutableMapping

if sys.version_info >= (3, 10):  # PEP 612
    from typing import ParamSpec
else:  # typing-extensions>=3.10.0
    from typing_extensions import ParamSpec

if sys.version_info >= (3, 12):  # various bug fixes and improvements
    from typing import Protocol
else:  # typing-extensions>=4.10.0
    from typing_extensions import Protocol

if sys.version_info >= (3, 11):  # python/cpython#31716: introspectable
    from typing import overload
else:  # typing-extensions>=4.2.0
    from typing_extensions import overload

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
    module_name: str,
    replacer: MissingType = MISSING,
    /,
) -> Callable[[_NamedCallableT], _NamedCallableT]: ...
@overload
def replaces_when_imported(
    namespace: MutableMapping[str, Any],
    module_name: str,
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
