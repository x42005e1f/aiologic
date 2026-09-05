#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from typing import TYPE_CHECKING

from aiologic.abc import BaseHandle

from ._states import ThreadState

if TYPE_CHECKING:
    from typing import Any

    from aiologic.process import ProcessHandle

    if sys.version_info >= (3, 11):
        from typing import Never
    else:
        from typing_extensions import Never

if sys.version_info >= (3, 11):
    from typing import final
else:
    from typing_extensions import final


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
