#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from collections.abc import Callable, Iterable, Mapping, MutableMapping
from types import ModuleType
from typing import Any, Literal, TypeVar, overload

from ._markers import MISSING, MissingType

_HookT = TypeVar("_HookT", bound=Callable[[ModuleType], Any])
_UHookT = TypeVar("_UHookT", bound=Callable[[ModuleType | None], Any])

@overload
def when_imported_for(
    namespace: MutableMapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    hook: _UHookT,
    /,
    *,
    name: str,
    empty_ok: Literal[True],
) -> _UHookT: ...
@overload
def when_imported_for(
    namespace: MutableMapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    hook: MissingType = MISSING,
    /,
    *,
    name: str,
    empty_ok: Literal[True],
) -> Callable[[_UHookT], _UHookT]: ...
@overload
def when_imported_for(
    namespace: Mapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    hook: _UHookT,
    /,
    *,
    name: None = None,
    empty_ok: Literal[True],
) -> _UHookT: ...
@overload
def when_imported_for(
    namespace: Mapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    hook: MissingType = MISSING,
    /,
    *,
    name: None = None,
    empty_ok: Literal[True],
) -> Callable[[_UHookT], _UHookT]: ...
@overload
def when_imported_for(
    namespace: MutableMapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    hook: _HookT,
    /,
    *,
    name: str,
    empty_ok: Literal[False] = False,
) -> _HookT: ...
@overload
def when_imported_for(
    namespace: MutableMapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    hook: MissingType = MISSING,
    /,
    *,
    name: str,
    empty_ok: Literal[False] = False,
) -> Callable[[_HookT], _HookT]: ...
@overload
def when_imported_for(
    namespace: Mapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    hook: _HookT,
    /,
    *,
    name: None = None,
    empty_ok: Literal[False] = False,
) -> _HookT: ...
@overload
def when_imported_for(
    namespace: Mapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    hook: MissingType = MISSING,
    /,
    *,
    name: None = None,
    empty_ok: Literal[False] = False,
) -> Callable[[_HookT], _HookT]: ...
