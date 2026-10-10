#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

_TSO_MACHINES = frozenset({
    # x86(-64)
    "i386",
    "i386-at386",
    "i486",
    "i486-at386",
    "i586",
    "i586-at386",
    "i686",
    "i686-at386",
    "i86pc",
    "x86pc",
    "x86",
    "x86_64",
    "amd64",
    # ESA/390
    "s390",
    # z/Architecture
    "s390x",
})

try:
    from sys import _is_gil_enabled  # python/cpython#118514
except ImportError:
    _is_nogil = bool  # () -> Literal[False]
    _is_notso = bool  # () -> Literal[False]
else:
    import platform

    _is_tso_machine = platform.machine().lower() in _TSO_MACHINES

    def _is_nogil():
        global _is_nogil

        is_gil = _is_gil_enabled()
        if is_gil:
            _is_nogil = bool  # () -> Literal[False]

        return not is_gil

    def _is_notso():
        global _is_notso

        is_tso = _is_tso_machine or _is_gil_enabled()
        if is_tso:
            _is_notso = bool  # () -> Literal[False]

        return not is_tso

    _is_nogil()  # to try to optimize
    _is_notso()  # to try to optimize


def is_nogil() -> bool:
    return _is_nogil()


def is_notso() -> bool:
    return _is_notso()
