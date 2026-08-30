#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

"""
This package implements thread-level functions and primitives that are not
subject to monkey patching by green libraries. It exists primarily to implement
low-level features, but in a sense it can also be considered a special toolkit
for the patched world.
"""

from ._handles import (
    BaseHandle as BaseHandle,
    ThreadHandle as ThreadHandle,
)
from ._states import (
    BaseState as BaseState,
    StateReferenceKey as StateReferenceKey,
    ThreadState as ThreadState,
)
from ._threads import (
    current_thread as current_thread,
    current_thread_ident as current_thread_ident,
    current_thread_state as current_thread_state,
)
from ._vars import (
    BaseVar as BaseVar,
    BaseVarToken as BaseVarToken,
    ThreadVar as ThreadVar,
    ThreadVarToken as ThreadVarToken,
)
