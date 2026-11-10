#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import platform
import sys

# see https://wiki.debian.org/ArchitectureSpecificsMemo (uname -m)
_is_tso_machine = platform.machine().lower() in {
    # x86(-64)
    "i386",
    "i386-at386",
    "i486",
    "i486-at386",
    "i586",
    "i586-at386",
    "i686",
    "i686-at386",
    "i86pc",  # Solaris | illumos
    "x86pc",  # QNX
    "x86",  # Windows
    "x86_64",
    "amd64",  # Windows
    # ESA/390
    "s390",
    # z/Architecture
    "s390x",
}

_is_nogil_flag = not getattr(sys.flags, "gil", 1)
_is_notso_flag = not getattr(sys.flags, "gil", 1) and not _is_tso_machine


def is_nogil() -> bool:
    return _is_nogil_flag


def is_notso() -> bool:
    return _is_notso_flag
