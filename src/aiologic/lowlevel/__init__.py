#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

"""
This package implements building blocks for top-level primitives, specifically
low-level primitives, and a number of important mechanisms such as checkpoints.

You can use its contents to create your own primitives or fine-tune existing
ones. In addition, it also provides features that are useful on their own.
"""

from ._checkpoints import (
    async_checkpoint as async_checkpoint,
    async_checkpoint_enabled as async_checkpoint_enabled,
    async_checkpoint_if_cancelled as async_checkpoint_if_cancelled,
    disable_checkpoints as disable_checkpoints,
    enable_checkpoints as enable_checkpoints,
    green_checkpoint as green_checkpoint,
    green_checkpoint_enabled as green_checkpoint_enabled,
    green_checkpoint_if_cancelled as green_checkpoint_if_cancelled,
)
from ._events import (
    CANCELLED_EVENT as CANCELLED_EVENT,
    DUMMY_EVENT as DUMMY_EVENT,
    SET_EVENT as SET_EVENT,
    AsyncEvent as AsyncEvent,
    CancelledEvent as CancelledEvent,
    DummyEvent as DummyEvent,
    Event as Event,
    GreenEvent as GreenEvent,
    SetEvent as SetEvent,
    create_async_event as create_async_event,
    create_green_event as create_green_event,
)
from ._ident import (
    current_async_task as current_async_task,
    current_async_task_ident as current_async_task_ident,
    current_async_token as current_async_token,
    current_async_token_ident as current_async_token_ident,
    current_green_task as current_green_task,
    current_green_task_ident as current_green_task_ident,
    current_green_token as current_green_token,
    current_green_token_ident as current_green_token_ident,
)
from ._libraries import (
    AsyncLibraryNotFoundError as AsyncLibraryNotFoundError,
    GreenLibraryNotFoundError as GreenLibraryNotFoundError,
    current_async_library as current_async_library,
    current_async_library_tlocal as current_async_library_tlocal,
    current_green_library as current_green_library,
    current_green_library_tlocal as current_green_library_tlocal,
)
from ._locks import (
    THREAD_DUMMY_LOCK as THREAD_DUMMY_LOCK,
    ThreadDummyLock as ThreadDummyLock,
    ThreadLock as ThreadLock,
    ThreadOnceLock as ThreadOnceLock,
    ThreadRLock as ThreadRLock,
    create_thread_lock as create_thread_lock,
    create_thread_oncelock as create_thread_oncelock,
    create_thread_rlock as create_thread_rlock,
    once as once,
)
from ._queues import (
    lazydeque as lazydeque,
    lazyqueue as lazyqueue,
)
from ._safety import (
    disable_signal_safety as disable_signal_safety,
    enable_signal_safety as enable_signal_safety,
    signal_safety_enabled as signal_safety_enabled,
)
from ._tasks import (
    shield as shield,
)
from ._threads import (
    current_thread as current_thread,
    current_thread_ident as current_thread_ident,
)
from ._time import (
    async_clock as async_clock,
    async_seconds_per_sleep as async_seconds_per_sleep,
    async_seconds_per_timeout as async_seconds_per_timeout,
    async_sleep as async_sleep,
    async_sleep_forever as async_sleep_forever,
    async_sleep_until as async_sleep_until,
    green_clock as green_clock,
    green_seconds_per_sleep as green_seconds_per_sleep,
    green_seconds_per_timeout as green_seconds_per_timeout,
    green_sleep as green_sleep,
    green_sleep_forever as green_sleep_forever,
    green_sleep_until as green_sleep_until,
)
from ._waiters import (
    AsyncWaiter as AsyncWaiter,
    GreenWaiter as GreenWaiter,
    Waiter as Waiter,
    create_async_waiter as create_async_waiter,
    create_green_waiter as create_green_waiter,
)
