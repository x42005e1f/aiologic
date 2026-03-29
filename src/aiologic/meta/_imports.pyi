#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from types import ModuleType
from typing import Any

if sys.version_info >= (3, 11):  # python/cpython#31716: introspectable
    from typing import overload
else:  # typing-extensions>=4.2.0
    from typing_extensions import overload

def import_module(name: str, package: str | None = None) -> ModuleType: ...
@overload
def import_from(
    module: ModuleType | str,
    name0: str,
    /,
    *,
    package: str | None = None,
) -> Any: ...
@overload
def import_from(
    module: ModuleType | str,
    name0: str,
    name1: str,
    /,
    *names: str,
    package: str | None = None,
) -> tuple[Any, ...]: ...
@overload
def import_original(
    module: ModuleType | str,
    name0: str,
    /,
    *,
    package: str | None = None,
) -> Any: ...
@overload
def import_original(
    module: ModuleType | str,
    name0: str,
    name1: str,
    /,
    *names: str,
    package: str | None = None,
) -> tuple[Any, ...]: ...
def isgreenpatched(module: ModuleType | str, /) -> bool: ...
