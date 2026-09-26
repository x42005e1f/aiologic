#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from typing import Any, Never, final

from aiologic.abc import BaseHandle
from aiologic.process import ProcessHandle

from ._states import ThreadState

@final
class ThreadHandle(BaseHandle[ThreadState]):
    __slots__ = ("_process",)

    def __init__(
        self,
        /,
        process: ProcessHandle,
        state: ThreadState,
        ident: int,
    ) -> None: ...
    def __init_subclass__(cls, /, **kwargs: Any) -> Never: ...
    @property
    def process(self, /) -> ProcessHandle: ...
