#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from types import FunctionType
from typing import TYPE_CHECKING, Any

if sys.version_info >= (3, 11):
    from typing import get_overloads, overload
else:
    from typing_extensions import get_overloads, overload


def export(namespace: dict[str, Any], /) -> None:
    """..."""

    if TYPE_CHECKING:
        # sphinx.ext.autodoc does not support hacks below. In particular,
        # 'bysource' ordering will not work, nor will some cross-references. So
        # we skip them on type checking (implied by
        # SPHINX_AUTODOC_RELOAD_MODULES=1).
        return

    module_name: str = namespace["__name__"]

    for value in namespace.values():
        if getattr(value, "__module__", "").startswith(f"{module_name}."):
            if isinstance(value, FunctionType):
                # We have to re-register overloads before updating the
                # function's __module__, as it is used by get_overloads() as
                # one of the registry keys.
                for value_overload in get_overloads(value):
                    value_overload.__module__ = module_name

                    # re-register value_overload for module_name
                    overload(value_overload)

            try:
                value.__module__ = module_name
            except AttributeError:  # a singleton object, etc.
                pass

        if getattr(value, "__name__", "").startswith(f"{module_name}."):
            package_name, _, submodule_name = value.__name__.rpartition(".")

            if package_name != module_name or submodule_name.startswith("_"):
                # skip indirect/private modules
                continue

            export(vars(value))
