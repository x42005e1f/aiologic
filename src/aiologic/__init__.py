#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from . import (  # noqa: F401
    lowlevel,
)
from ._barrier import (
    Barrier as Barrier,
    BrokenBarrierError as BrokenBarrierError,
    Latch as Latch,
)
from ._condition import (
    Condition as Condition,
)
from ._event import (
    CountdownEvent as CountdownEvent,
    Event as Event,
    REvent as REvent,
)
from ._guard import (
    BusyResourceError as BusyResourceError,
    ResourceGuard as ResourceGuard,
)
from ._limiter import (
    CapacityLimiter as CapacityLimiter,
    RCapacityLimiter as RCapacityLimiter,
)
from ._lock import (
    Lock as Lock,
    PLock as PLock,
    RLock as RLock,
)
from ._queue import (
    LifoQueue as LifoQueue,
    PriorityQueue as PriorityQueue,
    Queue as Queue,
    QueueEmpty as QueueEmpty,
    QueueFull as QueueFull,
    SimpleQueue as SimpleQueue,
)
from ._semaphore import (
    BoundedSemaphore as BoundedSemaphore,
    Semaphore as Semaphore,
)

# modify __module__ for shorter repr() and better pickle support
for __value in list(globals().values()):
    if getattr(__value, "__module__", "").startswith(f"{__name__}."):
        try:
            __value.__module__ = __name__
        except AttributeError:
            pass

    del __value
