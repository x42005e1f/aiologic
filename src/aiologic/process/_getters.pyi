#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from ._handles import ProcessHandle
from ._states import ProcessState

def current_process_ident() -> int: ...
def current_process_state() -> ProcessState: ...
def current_process() -> ProcessHandle: ...
