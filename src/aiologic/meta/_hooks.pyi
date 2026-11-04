#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from collections.abc import Callable, Iterable, Mapping, MutableMapping
from types import ModuleType
from typing import Any, Literal, TypeVar, overload

from ._markers import DEFAULT, MISSING, DefaultType, MissingType

_HookT = TypeVar("_HookT", bound=Callable[[ModuleType], Any])
_UHookT = TypeVar("_UHookT", bound=Callable[[ModuleType | None], Any])

@overload
def when_imported_for(
    namespace: MutableMapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    hook: _UHookT,
    /,
    *,
    empty_ok: Literal[True],
    parents: bool = False,
    package: str | None | DefaultType = DEFAULT,
    name: str,
) -> _UHookT: ...
@overload
def when_imported_for(
    namespace: MutableMapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    hook: MissingType = MISSING,
    /,
    *,
    empty_ok: Literal[True],
    parents: bool = False,
    package: str | None | DefaultType = DEFAULT,
    name: str,
) -> Callable[[_UHookT], _UHookT]: ...
@overload
def when_imported_for(
    namespace: Mapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    hook: _UHookT,
    /,
    *,
    empty_ok: Literal[True],
    parents: bool = False,
    package: str | None | DefaultType = DEFAULT,
    name: None = None,
) -> _UHookT: ...
@overload
def when_imported_for(
    namespace: Mapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    hook: MissingType = MISSING,
    /,
    *,
    empty_ok: Literal[True],
    parents: bool = False,
    package: str | None | DefaultType = DEFAULT,
    name: None = None,
) -> Callable[[_UHookT], _UHookT]: ...
@overload
def when_imported_for(
    namespace: MutableMapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    hook: _HookT,
    /,
    *,
    empty_ok: Literal[False] = False,
    parents: bool = False,
    package: str | None | DefaultType = DEFAULT,
    name: str,
) -> _HookT: ...
@overload
def when_imported_for(
    namespace: MutableMapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    hook: MissingType = MISSING,
    /,
    *,
    empty_ok: Literal[False] = False,
    parents: bool = False,
    package: str | None | DefaultType = DEFAULT,
    name: str,
) -> Callable[[_HookT], _HookT]: ...
@overload
def when_imported_for(
    namespace: Mapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    hook: _HookT,
    /,
    *,
    empty_ok: Literal[False] = False,
    parents: bool = False,
    package: str | None | DefaultType = DEFAULT,
    name: None = None,
) -> _HookT: ...
@overload
def when_imported_for(
    namespace: Mapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    hook: MissingType = MISSING,
    /,
    *,
    empty_ok: Literal[False] = False,
    parents: bool = False,
    package: str | None | DefaultType = DEFAULT,
    name: None = None,
) -> Callable[[_HookT], _HookT]: ...
