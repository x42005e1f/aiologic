#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations


def resolve_name(name: str, package: str | None) -> str:
    """
    Resolve a relative module name to an absolute one.

    Like :func:`importlib.util.resolve_name`, but raises :exc:`ValueError`
    instead of :exc:`ImportError` on Python ≥3.9 to achieve consistent
    behavior across all supported versions of Python.

    Example:
      >>> resolve_name('.', 'a.b')
      'a.b'
      >>> resolve_name('x.y', 'a.b')
      'x.y'
      >>> resolve_name('.x.y', 'a.b')
      'a.b.x.y'
      >>> resolve_name('..x.y', 'a.b')
      'a.x.y'
      >>> resolve_name('...x.y', 'a.b')
      Traceback (most recent call last):
      ValueError: `name` is beyond the top-level package
    """

    if not name.startswith("."):
        return name
    elif not package:
        msg = (
            f"no package specified for {name!r}"
            " (required for relative module names)"
        )
        raise ValueError(msg)

    shifted_name = name.lstrip(".")
    shifted_name_level = len(name) - len(shifted_name)

    package_parts = package.rsplit(".", shifted_name_level - 1)

    if len(package_parts) < shifted_name_level:
        msg = "`name` is beyond the top-level package"
        raise ValueError(msg)

    if shifted_name:
        return f"{package_parts[0]}.{shifted_name}"

    return package_parts[0]
