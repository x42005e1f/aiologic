#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

from aiologic.meta import DEFAULT, DefaultType, replaces

from ._executors import TaskExecutor, current_executor

if TYPE_CHECKING:
    import sys

    if sys.version_info >= (3, 9):
        from collections.abc import Generator
        from contextlib import AbstractContextManager
    else:
        from typing import ContextManager as AbstractContextManager, Generator


@contextmanager
def _assert_threading_checkpoints(
    expected: bool,
) -> Generator[None]:
    yield


def _assert_eventlet_checkpoints(
    expected: bool,
) -> AbstractContextManager[None]:
    from eventlet.hubs import get_hub

    def noop() -> None:
        pass

    @replaces(globals())
    @contextmanager
    def _assert_eventlet_checkpoints(expected):
        timer = get_hub().schedule_call_local(0, noop)

        try:
            yield

            if timer.pending == expected:
                if expected:
                    msg = "assert_checkpoints block did not yield!"
                else:
                    msg = "assert_no_checkpoints block yielded!"

                raise AssertionError(msg)
        finally:
            timer.cancel()

    return _assert_eventlet_checkpoints(expected)


def _assert_gevent_checkpoints(expected: bool) -> AbstractContextManager[None]:
    from gevent import get_hub

    def noop() -> None:
        pass

    @replaces(globals())
    @contextmanager
    def _assert_gevent_checkpoints(expected):
        callback = get_hub().loop.run_callback(noop)

        try:
            yield

            if callback.pending == expected:
                if expected:
                    msg = "assert_checkpoints block did not yield!"
                else:
                    msg = "assert_no_checkpoints block yielded!"

                raise AssertionError(msg)
        finally:
            callback.close()

    return _assert_gevent_checkpoints(expected)


def _assert_asyncio_checkpoints(
    expected: bool,
) -> AbstractContextManager[None]:
    from asyncio import get_running_loop

    @replaces(globals())
    @contextmanager
    def _assert_asyncio_checkpoints(expected):
        yielded = False

        def callback():
            nonlocal yielded

            yielded = True

        handle = get_running_loop().call_soon(callback)

        try:
            yield

            if yielded != expected:
                if expected:
                    msg = "assert_checkpoints block did not yield!"
                else:
                    msg = "assert_no_checkpoints block yielded!"

                raise AssertionError(msg)
        finally:
            handle.cancel()

    return _assert_asyncio_checkpoints(expected)


def _assert_curio_checkpoints(expected: bool) -> AbstractContextManager[None]:
    from aiologic.lowlevel import current_async_task

    @replaces(globals())
    @contextmanager
    def _assert_curio_checkpoints(expected):
        task = current_async_task()
        task_cycles = task.cycles

        try:
            yield

            if (task_cycles != task.cycles) != expected:
                if expected:
                    msg = "assert_checkpoints block did not yield!"
                else:
                    msg = "assert_no_checkpoints block yielded!"

                raise AssertionError(msg)
        finally:
            del task

    return _assert_curio_checkpoints(expected)


def _assert_trio_checkpoints(expected: bool) -> AbstractContextManager[None]:
    from trio.testing import assert_checkpoints, assert_no_checkpoints

    @replaces(globals())
    def _assert_trio_checkpoints(expected):
        if expected:
            return assert_checkpoints()
        else:
            return assert_no_checkpoints()

    return _assert_trio_checkpoints(expected)


def assert_checkpoints(
    *,
    executor: TaskExecutor | DefaultType = DEFAULT,
) -> AbstractContextManager[None]:
    if executor is DEFAULT:
        executor = current_executor()

    backend = executor.backend

    if backend == "threading":
        impl = _assert_threading_checkpoints
    elif backend == "eventlet":
        impl = _assert_eventlet_checkpoints
    elif backend == "gevent":
        impl = _assert_gevent_checkpoints
    elif backend == "asyncio":
        impl = _assert_asyncio_checkpoints
    elif backend == "curio":
        impl = _assert_curio_checkpoints
    elif backend == "trio":
        impl = _assert_trio_checkpoints
    else:
        msg = f"unsupported backend {backend!r}"
        raise RuntimeError(msg)

    return impl(True)


def assert_no_checkpoints(
    *,
    executor: TaskExecutor | DefaultType = DEFAULT,
) -> AbstractContextManager[None]:
    if executor is DEFAULT:
        executor = current_executor()

    backend = executor.backend

    if backend == "threading":
        impl = _assert_threading_checkpoints
    elif backend == "eventlet":
        impl = _assert_eventlet_checkpoints
    elif backend == "gevent":
        impl = _assert_gevent_checkpoints
    elif backend == "asyncio":
        impl = _assert_asyncio_checkpoints
    elif backend == "curio":
        impl = _assert_curio_checkpoints
    elif backend == "trio":
        impl = _assert_trio_checkpoints
    else:
        msg = f"unsupported backend {backend!r}"
        raise RuntimeError(msg)

    return impl(False)
