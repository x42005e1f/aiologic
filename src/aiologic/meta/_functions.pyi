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

class _NamedCallable(Protocol):
    def __call__(self, /, *args: Any, **kwargs: Any) -> Any: ...
    @property
    def __name__(self, /) -> str: ...

_T = TypeVar("_T")
_NamedCallableT = TypeVar("_NamedCallableT", bound=_NamedCallable)
_P = ParamSpec("_P")

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

# Until python/typing#548 is resolved, we can only go one of two ways (not
# both):
# * require the parameter lists of both functions to match (via `ParamSpec`)
# * support callable subtypes, such as user-defined protocols (via `TypeVar`)
# Here, we choose the first way to prevent obvious type errors when applying
# the decorator to regular functions.
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
