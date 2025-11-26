#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

"""
GIL-powered* locking library for Python

This package is a locking library for tasks synchronization and their
communication. It provides primitives that are both *async-aware* and
*thread-aware*, and can be used for interaction between:

* async codes (async <-> async) in one thread as regular async primitives
* async codes (async <-> async) in multiple threads (!)
* async code and sync one (async <-> sync) in one thread (!)
* async code and sync one (async <-> sync) in multiple threads (!)
* sync codes (sync <-> sync) in one thread as regular sync primitives
* sync codes (sync <-> sync) in multiple threads as regular sync primitives

If you want to know more, visit https://aiologic.readthedocs.io.
"""

from __future__ import annotations

__author__: str = "Ilya Egorov <0x42005e1f@gmail.com>"
__version__: str  # dynamic
__version_tuple__: tuple[int | str, ...]  # dynamic

from . import (  # noqa: F401
    lowlevel,
    meta,
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
    Lock as Lock,
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

# prepare for external use
meta.export(globals())
meta.export_dynamic(globals(), "__version__", "._version.version")
meta.export_dynamic(globals(), "__version_tuple__", "._version.version_tuple")
