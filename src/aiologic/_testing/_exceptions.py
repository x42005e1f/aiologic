#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from aiologic.meta import DEFAULT, DefaultType, replaces

from ._executors import TaskExecutor, current_executor


def _get_threading_cancelled_exc_class() -> type[BaseException]:
    from concurrent.futures import CancelledError

    @replaces(globals())
    def _get_threading_cancelled_exc_class():
        return CancelledError

    return _get_threading_cancelled_exc_class()


def _get_eventlet_cancelled_exc_class() -> type[BaseException]:
    from greenlet import GreenletExit

    @replaces(globals())
    def _get_eventlet_cancelled_exc_class():
        return GreenletExit

    return _get_eventlet_cancelled_exc_class()


def _get_gevent_cancelled_exc_class() -> type[BaseException]:
    from greenlet import GreenletExit

    @replaces(globals())
    def _get_gevent_cancelled_exc_class():
        return GreenletExit

    return _get_gevent_cancelled_exc_class()


def _get_asyncio_cancelled_exc_class() -> type[BaseException]:
    from asyncio import CancelledError

    @replaces(globals())
    def _get_asyncio_cancelled_exc_class():
        return CancelledError

    return _get_asyncio_cancelled_exc_class()


def _get_curio_cancelled_exc_class() -> type[BaseException]:
    from curio import TaskCancelled

    @replaces(globals())
    def _get_curio_cancelled_exc_class():
        return TaskCancelled

    return _get_curio_cancelled_exc_class()


def _get_trio_cancelled_exc_class() -> type[BaseException]:
    from trio import Cancelled

    @replaces(globals())
    def _get_trio_cancelled_exc_class():
        return Cancelled

    return _get_trio_cancelled_exc_class()


def get_cancelled_exc_class(
    *,
    executor: TaskExecutor | DefaultType = DEFAULT,
    failback: type[BaseException] | None = None,
) -> type[BaseException]:
    if executor is DEFAULT:
        if failback is None:
            executor = current_executor()
        else:
            executor = current_executor(failsafe=True)

            if executor is None:
                return failback

    backend = executor.backend

    if backend == "threading":
        return _get_threading_cancelled_exc_class()

    if backend == "eventlet":
        return _get_eventlet_cancelled_exc_class()

    if backend == "gevent":
        return _get_gevent_cancelled_exc_class()

    if backend == "asyncio":
        return _get_asyncio_cancelled_exc_class()

    if backend == "curio":
        return _get_curio_cancelled_exc_class()

    if backend == "trio":
        return _get_trio_cancelled_exc_class()

    msg = f"unsupported backend {backend!r}"
    raise RuntimeError(msg)


def _get_threading_timeout_exc_class() -> type[BaseException]:
    if sys.version_info >= (3, 11):
        from builtins import TimeoutError as WaitTimeout
    else:
        from concurrent.futures import TimeoutError as WaitTimeout

    @replaces(globals())
    def _get_threading_timeout_exc_class():
        return WaitTimeout

    return _get_threading_timeout_exc_class()


def _get_eventlet_timeout_exc_class() -> type[BaseException]:
    from eventlet import Timeout

    @replaces(globals())
    def _get_eventlet_timeout_exc_class():
        return Timeout

    return _get_eventlet_timeout_exc_class()


def _get_gevent_timeout_exc_class() -> type[BaseException]:
    from gevent import Timeout

    @replaces(globals())
    def _get_gevent_timeout_exc_class():
        return Timeout

    return _get_gevent_timeout_exc_class()


def _get_asyncio_timeout_exc_class() -> type[BaseException]:
    if sys.version_info >= (3, 11):
        from builtins import TimeoutError as WaitTimeout
    else:
        from asyncio import TimeoutError as WaitTimeout

    @replaces(globals())
    def _get_asyncio_timeout_exc_class():
        return WaitTimeout

    return _get_asyncio_timeout_exc_class()


def _get_curio_timeout_exc_class() -> type[BaseException]:
    from curio import TaskTimeout

    @replaces(globals())
    def _get_curio_timeout_exc_class():
        return TaskTimeout

    return _get_curio_timeout_exc_class()


def _get_trio_timeout_exc_class() -> type[BaseException]:
    from trio import TooSlowError

    @replaces(globals())
    def _get_trio_timeout_exc_class():
        return TooSlowError

    return _get_trio_timeout_exc_class()


def _get_anyio_timeout_exc_class() -> type[BaseException]:
    return TimeoutError


def get_timeout_exc_class(
    *,
    executor: TaskExecutor | DefaultType = DEFAULT,
    failback: type[BaseException] | None = None,
) -> type[BaseException]:
    if executor is DEFAULT:
        if failback is None:
            executor = current_executor()
        else:
            executor = current_executor(failsafe=True)

            if executor is None:
                return failback

    library = executor.library

    if library == "threading":
        return _get_threading_timeout_exc_class()

    if library == "eventlet":
        return _get_eventlet_timeout_exc_class()

    if library == "gevent":
        return _get_gevent_timeout_exc_class()

    if library == "asyncio":
        return _get_asyncio_timeout_exc_class()

    if library == "curio":
        return _get_curio_timeout_exc_class()

    if library == "trio":
        return _get_trio_timeout_exc_class()

    if library == "anyio":
        return _get_anyio_timeout_exc_class()

    msg = f"unsupported library {library!r}"
    raise RuntimeError(msg)


_CancelledError: type[BaseException] = _get_threading_cancelled_exc_class()
_TimeoutError: type[BaseException] = _get_threading_timeout_exc_class()
