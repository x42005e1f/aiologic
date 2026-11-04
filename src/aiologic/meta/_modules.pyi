#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

def resolve_name(name: str, package: str | None) -> str: ...
def resolve_name_with_parents(name: str, package: str | None) -> list[str]: ...
