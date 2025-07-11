#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from ._constants import (
    ASYNC_PAIRS as ASYNC_PAIRS,
    GREEN_PAIRS as GREEN_PAIRS,
)
from ._exceptions import (
    get_cancelled_exc_class as get_cancelled_exc_class,
    get_timeout_exc_class as get_timeout_exc_class,
)
from ._executors import (
    TaskExecutor as TaskExecutor,
    create_executor as create_executor,
    current_executor as current_executor,
)
from ._results import (
    Result as Result,
)
from ._runners import (
    run as run,
)
from ._tasks import (
    Task as Task,
    create_task as create_task,
)

# modify __module__ for shorter repr()
if not __import__("typing").TYPE_CHECKING:
    for __value in list(globals().values()):
        if getattr(__value, "__module__", "").startswith(f"{__name__}."):
            try:
                __value.__module__ = __name__
            except AttributeError:
                pass

        del __value
