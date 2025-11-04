#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from ._originals import (
    import_original as import_original,
    patched as patched,
)
from ._patcher import (
    patch_eventlet as patch_eventlet,
)
