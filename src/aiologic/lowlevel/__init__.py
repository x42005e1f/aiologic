#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from ._checkpoints import (
    async_checkpoint as async_checkpoint,
    async_checkpoint_enabled as async_checkpoint_enabled,
    async_checkpoint_if_cancelled as async_checkpoint_if_cancelled,
    checkpoint as checkpoint,
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
from ._flags import (
    Flag as Flag,
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
from ._markers import (
    DEFAULT as DEFAULT,
    MISSING as MISSING,
    DefaultType as DefaultType,
    MissingType as MissingType,
)
from ._tasks import (
    shield as shield,
)
from ._threads import (
    current_thread as current_thread,
    current_thread_ident as current_thread_ident,
)
from ._waiters import (
    AsyncWaiter as AsyncWaiter,
    GreenWaiter as GreenWaiter,
    Waiter as Waiter,
    create_async_waiter as create_async_waiter,
    create_green_waiter as create_green_waiter,
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
