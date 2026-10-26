#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

from typing import TYPE_CHECKING, final

from aiologic.abc import BaseState
from aiologic.meta import getname_static

if TYPE_CHECKING:
    from typing import Any, Never


@final
class ProcessState(BaseState):
    __slots__ = ()

    def __init_subclass__(cls, /, **kwargs: Any) -> Never:
        bcs = __class__
        bcs_name = getname_static(bcs)

        msg = f"type {bcs_name!r} is not an acceptable base type"
        raise TypeError(msg)
