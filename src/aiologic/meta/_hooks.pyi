#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from collections.abc import Callable, Iterable, MutableMapping
from types import ModuleType
from typing import Any, TypeVar, overload

from ._markers import MISSING, MissingType

_HookT = TypeVar("_HookT", bound=Callable[[ModuleType], Any])

@overload
def when_imported_for(
    namespace: MutableMapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    hook: MissingType = MISSING,
    /,
    *,
    name: str | MissingType = MISSING,
) -> Callable[[_HookT], _HookT]: ...
@overload
def when_imported_for(
    namespace: MutableMapping[str, Any],
    module_name_or_info: str | Iterable[str | Iterable[str]],
    hook: _HookT,
    /,
    *,
    name: str | MissingType = MISSING,
) -> _HookT: ...
