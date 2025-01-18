#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from .barrier import (
    Barrier as Barrier,
    BrokenBarrierError as BrokenBarrierError,
    Latch as Latch,
)
from .condition import (
    Condition as Condition,
)
from .event import (
    CountdownEvent as CountdownEvent,
    Event as Event,
    REvent as REvent,
)
from .guard import (
    BusyResourceError as BusyResourceError,
    ResourceGuard as ResourceGuard,
)
from .limiter import (
    CapacityLimiter as CapacityLimiter,
    RCapacityLimiter as RCapacityLimiter,
)
from .lock import (
    Lock as Lock,
    PLock as PLock,
    RLock as RLock,
)
from .queue import (
    LifoQueue as LifoQueue,
    PriorityQueue as PriorityQueue,
    Queue as Queue,
    QueueEmpty as QueueEmpty,
    QueueFull as QueueFull,
    SimpleQueue as SimpleQueue,
)
from .semaphore import (
    BoundedSemaphore as BoundedSemaphore,
    Semaphore as Semaphore,
)

# add aiologic.locks subpackage for backward compatibility with 0.12.0
__modules = __import__("sys").modules
__modules[f"{__name__}.locks"] = __modules[f"{__name__}"]
__modules[f"{__name__}.locks.barrier"] = __modules[f"{__name__}.barrier"]
__modules[f"{__name__}.locks.condition"] = __modules[f"{__name__}.condition"]
__modules[f"{__name__}.locks.event"] = __modules[f"{__name__}.event"]
__modules[f"{__name__}.locks.guard"] = __modules[f"{__name__}.guard"]
__modules[f"{__name__}.locks.limiter"] = __modules[f"{__name__}.limiter"]
__modules[f"{__name__}.locks.lock"] = __modules[f"{__name__}.lock"]
__modules[f"{__name__}.locks.semaphore"] = __modules[f"{__name__}.semaphore"]

del __modules

# modify __module__ for shorter repr() and better pickle support
for __value in list(globals().values()):
    if getattr(__value, "__module__", "").startswith(f"{__name__}."):
        try:
            __value.__module__ = __name__
        except AttributeError:
            pass

del __value
