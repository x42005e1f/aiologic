#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from typing import Any

_registry: dict[str, dict[tuple[str, str], Any]]

def export_deprecated(
    namespace: dict[str, Any],
    source_name: str,
    target_name: str,
    /,
) -> None: ...
def export(namespace: dict[str, Any], /) -> None: ...
