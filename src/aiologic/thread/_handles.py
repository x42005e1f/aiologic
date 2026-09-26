#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

from typing import TYPE_CHECKING, final

from aiologic.abc import BaseHandle

from ._states import ThreadState

if TYPE_CHECKING:
    from typing import Any, Never

    from aiologic.process import ProcessHandle


@final
class ThreadHandle(BaseHandle[ThreadState]):
    __slots__ = ("_process",)

    def __init__(
        self,
        /,
        process: ProcessHandle,
        state: ThreadState,
        ident: int,
    ) -> None:
        super().__init__(state, ident)

        self._process = process

    def __init_subclass__(cls, /, **kwargs: Any) -> Never:
        bcs = __class__
        bcs_name = bcs.__name__

        msg = f"type {bcs_name!r} is not an acceptable base type"
        raise TypeError(msg)

    @property
    def process(self, /) -> ProcessHandle:
        return self._process
