#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from typing import Any, Never, final

from aiologic.abc import BaseState

@final
class ProcessState(BaseState):
    __slots__ = ()

    def __init_subclass__(cls, /, **kwargs: Any) -> Never: ...
