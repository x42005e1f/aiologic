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
    RBarrier as RBarrier,
)
from ._condition import (
    Condition as Condition,
)
from ._decorator import (
    synchronized as synchronized,
)
from ._event import (
    CountdownEvent as CountdownEvent,
    Event as Event,
    REvent as REvent,
)
from ._flag import (
    Flag as Flag,
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
    BLock as BLock,
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
    SimpleLifoQueue as SimpleLifoQueue,
    SimpleQueue as SimpleQueue,
)
from ._semaphore import (
    BinarySemaphore as BinarySemaphore,
    BoundedBinarySemaphore as BoundedBinarySemaphore,
    BoundedSemaphore as BoundedSemaphore,
    Semaphore as Semaphore,
)

# modify __module__ for shorter repr() and better pickle support
if not __import__("typing").TYPE_CHECKING:
    for __value in list(globals().values()):
        if getattr(__value, "__module__", "").startswith(f"{__name__}."):
            try:
                __value.__module__ = __name__
            except AttributeError:
                pass

        del __value
