#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from types import ModuleType

from ._markers import DEFAULT, DefaultType

def _issubmodule(module_name: str | None, package_name: str, /) -> bool: ...
def _export_one(
    package_name: str,
    qualname: str,
    name: str,
    value: object,
    /,
    *,
    visited: set[int] | DefaultType = DEFAULT,
) -> None: ...
def export(package_namespace: ModuleType | dict[str, object], /) -> None: ...
def _register(
    module_namespace: ModuleType | dict[str, object],
    link_name: str,
    target: str,
    /,
    *,
    deprecated: bool,
) -> None: ...
def export_dynamic(
    module_namespace: ModuleType | dict[str, object],
    link_name: str,
    target: str,
    /,
) -> None: ...
def export_deprecated(
    module_namespace: ModuleType | dict[str, object],
    link_name: str,
    target: str,
    /,
) -> None: ...
