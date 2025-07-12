#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from contextlib import contextmanager

from ._executors import TaskExecutor

if sys.version_info >= (3, 9):
    from collections.abc import Generator
    from contextlib import AbstractContextManager
else:
    from typing import ContextManager as AbstractContextManager, Generator

@contextmanager
def _assert_threading_checkpoints(
    expected: bool,
) -> Generator[None, None, None]: ...
def _assert_eventlet_checkpoints(
    expected: bool,
) -> AbstractContextManager[None]: ...
def _assert_gevent_checkpoints(
    expected: bool,
) -> AbstractContextManager[None]: ...
def _assert_asyncio_checkpoints(
    expected: bool,
) -> AbstractContextManager[None]: ...
def _assert_curio_checkpoints(
    expected: bool,
) -> AbstractContextManager[None]: ...
def _assert_trio_checkpoints(
    expected: bool,
) -> AbstractContextManager[None]: ...
def assert_checkpoints(
    *,
    executor: TaskExecutor | None = None,
) -> AbstractContextManager[None]: ...
def assert_no_checkpoints(
    *,
    executor: TaskExecutor | None = None,
) -> AbstractContextManager[None]: ...
