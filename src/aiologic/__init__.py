#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

__author__: str = "Ilya Egorov <0x42005e1f@gmail.com>"
__version__: str
__version_tuple__: tuple[int | str, ...]

from . import (  # ruff: ignore[unused-import]
    abc,
    lowlevel,
    meta,
    process,
    thread,
)
from ._barriers import (
    Barrier as Barrier,
    BrokenBarrierError as BrokenBarrierError,
    Latch as Latch,
    RBarrier as RBarrier,
)
from ._conditions import (
    Condition as Condition,
)
from ._decorators import (
    synchronized as synchronized,
)
from ._events import (
    CountdownEvent as CountdownEvent,
    Event as Event,
    REvent as REvent,
)
from ._flags import (
    Flag as Flag,
)
from ._guards import (
    BusyResourceError as BusyResourceError,
    ResourceGuard as ResourceGuard,
)
from ._limiters import (
    CapacityLimiter as CapacityLimiter,
    RCapacityLimiter as RCapacityLimiter,
)
from ._locks import (
    Lock as Lock,
    RLock as RLock,
)
from ._queues import (
    LifoQueue as LifoQueue,
    PriorityQueue as PriorityQueue,
    Queue as Queue,
    QueueEmpty as QueueEmpty,
    QueueFull as QueueFull,
    SimpleLifoQueue as SimpleLifoQueue,
    SimpleQueue as SimpleQueue,
)
from ._semaphores import (
    BinarySemaphore as BinarySemaphore,
    BoundedBinarySemaphore as BoundedBinarySemaphore,
    BoundedSemaphore as BoundedSemaphore,
    Semaphore as Semaphore,
)

meta.export(globals())
meta.export_dynamic(globals(), "__version__", "._version.version")
meta.export_dynamic(globals(), "__version_tuple__", "._version.version_tuple")
