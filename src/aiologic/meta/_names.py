#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

from itertools import accumulate


def _dotjoin2(a, b, /):
    # f-strings are too slow on PyPy for this case
    return a + "." + b


def resolve_name(name: str, /, package: str | None) -> str:
    if not name.startswith("."):
        return name

    if not package:
        msg = (
            f"no package specified for {name!r} (required for relative names)"
        )
        raise ValueError(msg)

    shifted_name = name.lstrip(".")
    shifted_name_offset = len(name) - len(shifted_name)

    package_parts = package.rsplit(".", shifted_name_offset - 1)

    if len(package_parts) != shifted_name_offset:
        msg = f"{name!r} is beyond the top-level package of {package!r}"
        raise ValueError(msg)

    base_name = package_parts[0]

    if shifted_name:
        return base_name + "." + shifted_name

    return base_name


def resolve_name_with_parents(name: str, /, package: str | None) -> list[str]:
    if not name.startswith("."):
        name_parts = name.split(".")

        if package:
            join_length = 1

            for name_part in name_parts:
                package_part, _, package = package.partition(".")

                if name_part == package_part:
                    join_length += 1
                else:
                    break

                if not package:
                    break

            if join_length > 1:
                name_parts = [
                    ".".join(name_parts[:join_length]),
                    *name_parts[join_length:],
                ]

        return [*accumulate(name_parts, _dotjoin2)]

    if not package:
        msg = (
            f"no package specified for {name!r} (required for relative names)"
        )
        raise ValueError(msg)

    shifted_name = name.lstrip(".")
    shifted_name_offset = len(name) - len(shifted_name)

    package_parts = package.rsplit(".", shifted_name_offset - 1)

    if len(package_parts) != shifted_name_offset:
        msg = f"{name!r} is beyond the top-level package of {package!r}"
        raise ValueError(msg)

    base_name = package_parts[0]

    if shifted_name:
        name_parts = shifted_name.split(".")
        name_parts[0] = base_name + "." + name_parts[0]

        return [*accumulate(name_parts, _dotjoin2)]

    return [base_name]
