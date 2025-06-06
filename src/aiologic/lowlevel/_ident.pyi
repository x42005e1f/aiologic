#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

def _current_eventlet_token() -> object: ...
def _current_gevent_token() -> object: ...
def _current_asyncio_token() -> object: ...
def _current_curio_token() -> object: ...
def _current_trio_token() -> object: ...
def current_green_token() -> object: ...
def current_async_token() -> object: ...
def current_green_token_ident() -> tuple[str, int]: ...
def current_async_token_ident() -> tuple[str, int]: ...
def _current_asyncio_task() -> object: ...
def _current_curio_task() -> object: ...
def _current_trio_task() -> object: ...
def current_green_task() -> object: ...
def current_async_task() -> object: ...
def current_green_task_ident() -> tuple[str, int]: ...
def current_async_task_ident() -> tuple[str, int]: ...
