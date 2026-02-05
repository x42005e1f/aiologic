#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

if sys.version_info >= (3, 9):  # PEP 585
    from collections.abc import Iterator
else:
    from typing import Iterator

def getsro(obj: object, /) -> Iterator[tuple[object, object | None, str]]: ...
