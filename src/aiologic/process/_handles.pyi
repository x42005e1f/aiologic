#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from typing import Any

from aiologic.abc import BaseHandle

from ._states import ProcessState

if sys.version_info >= (3, 11):
    from typing import Never
else:
    from typing_extensions import Never

if sys.version_info >= (3, 11):
    from typing import final
else:
    from typing_extensions import final

@final
class ProcessHandle(BaseHandle[ProcessState]):
    __slots__ = ()

    def __init_subclass__(cls, /, **kwargs: Any) -> Never: ...
