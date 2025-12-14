#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from typing import Any, Final, TypeVar, type_check_only

from ._markers import MISSING, MissingType

if sys.version_info >= (3, 9):  # PEP 585
    from collections.abc import Callable, MutableMapping
else:
    from typing import Callable, MutableMapping

if sys.version_info >= (3, 10):  # PEP 612
    from typing import ParamSpec
else:  # typing-extensions>=3.10.0
    from typing_extensions import ParamSpec

if sys.version_info >= (3, 13):  # various fixes and improvements
    from typing import Protocol
else:  # typing-extensions>=4.10.0
    from typing_extensions import Protocol

if sys.version_info >= (3, 11):  # runtime introspection support
    from typing import overload
else:  # typing-extensions>=4.2.0
    from typing_extensions import overload

@type_check_only
class _NamedCallable(Protocol):
    def __call__(self, /, *args: Any, **kwargs: Any) -> Any: ...
    @property
    def __name__(self, /) -> str: ...

_T = TypeVar("_T")
_NamedCallableT = TypeVar("_NamedCallableT", bound=_NamedCallable)
_P = ParamSpec("_P")

_SPHINX_AUTODOC_RELOAD_MODULES: Final[bool]

@overload
def replaces(
    namespace: MutableMapping[str, object],
    replacer: MissingType = MISSING,
    /,
) -> Callable[[_NamedCallableT], _NamedCallableT]: ...
@overload
def replaces(
    namespace: MutableMapping[str, object],
    replacer: _NamedCallableT,
    /,
) -> _NamedCallableT: ...
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
