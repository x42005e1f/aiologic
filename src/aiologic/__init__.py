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

# add aiologic.locks subpackage for backward compatibility with 0.12.0
__modules = __import__("sys").modules
__modules[f"{__name__}.locks"] = __modules[f"{__name__}"]
__modules[f"{__name__}.locks.barrier"] = __modules[f"{__name__}._barrier"]
__modules[f"{__name__}.locks.condition"] = __modules[f"{__name__}._condition"]
__modules[f"{__name__}.locks.event"] = __modules[f"{__name__}._event"]
__modules[f"{__name__}.locks.guard"] = __modules[f"{__name__}._guard"]
__modules[f"{__name__}.locks.limiter"] = __modules[f"{__name__}._limiter"]
__modules[f"{__name__}.locks.lock"] = __modules[f"{__name__}._lock"]
__modules[f"{__name__}.locks.semaphore"] = __modules[f"{__name__}._semaphore"]

del __modules

# modify __module__ for shorter repr() and better pickle support
for __value in list(globals().values()):
    if getattr(__value, "__module__", "").startswith(f"{__name__}."):
        try:
            __value.__module__ = __name__
        except AttributeError:
            pass

    del __value
