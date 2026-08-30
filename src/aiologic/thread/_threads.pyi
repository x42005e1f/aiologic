#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from ._handles import ThreadHandle
from ._states import ThreadState

def current_thread_ident() -> int: ...
def current_thread_state() -> ThreadState: ...
def current_thread() -> ThreadHandle: ...
