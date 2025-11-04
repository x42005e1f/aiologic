#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from inspect import isawaitable, iscoroutinefunction
from typing import TYPE_CHECKING, Any, TypeVar

from aiologic.meta import DEFAULT, DefaultType, replaces

from ._exceptions import get_cancelled_exc_class, get_timeout_exc_class
from ._executors import TaskExecutor, current_executor

if sys.version_info >= (3, 11):
    from typing import TypeVarTuple, Unpack, overload
else:
    from typing_extensions import TypeVarTuple, Unpack, overload

if TYPE_CHECKING:
    if sys.version_info >= (3, 9):
        from collections.abc import Awaitable, Callable, Coroutine
    else:
        from typing import Awaitable, Callable, Coroutine

_T = TypeVar("_T")
_Ts = TypeVarTuple("_Ts")


@overload
def _threading_timeout_after(
    seconds: float,
    maybe_func: Awaitable[_T],
    /,
) -> Coroutine[Any, Any, _T]: ...
@overload
def _threading_timeout_after(
    seconds: float,
    maybe_func: Callable[[Unpack[_Ts]], _T],
    /,
    *args: Unpack[_Ts],
) -> _T: ...
def _threading_timeout_after(seconds, maybe_func, /, *args):
    if not callable(maybe_func) or iscoroutinefunction(maybe_func):
        msg = f"a green function was expected, got {maybe_func!r}"
        raise TypeError(msg)

    return maybe_func(*args)


@overload
def _eventlet_timeout_after(
    seconds: float,
    maybe_func: Awaitable[_T],
    /,
) -> Coroutine[Any, Any, _T]: ...
@overload
def _eventlet_timeout_after(
    seconds: float,
    maybe_func: Callable[[Unpack[_Ts]], _T],
    /,
    *args: Unpack[_Ts],
) -> _T: ...
def _eventlet_timeout_after(seconds, maybe_func, /, *args):
    from eventlet.timeout import with_timeout

    @replaces(globals())
    def _eventlet_timeout_after(seconds, maybe_func, /, *args):
        if not callable(maybe_func) or iscoroutinefunction(maybe_func):
            msg = f"a green function was expected, got {maybe_func!r}"
            raise TypeError(msg)

        return with_timeout(max(0, seconds), maybe_func, *args)

    return _eventlet_timeout_after(seconds, maybe_func, *args)


@overload
def _gevent_timeout_after(
    seconds: float,
    maybe_func: Awaitable[_T],
    /,
) -> Coroutine[Any, Any, _T]: ...
@overload
def _gevent_timeout_after(
    seconds: float,
    maybe_func: Callable[[Unpack[_Ts]], _T],
    /,
    *args: Unpack[_Ts],
) -> _T: ...
def _gevent_timeout_after(seconds, maybe_func, /, *args):
    from gevent import Timeout, get_hub, getcurrent, with_timeout

    @replaces(globals())
    def _gevent_timeout_after(seconds, maybe_func, /, *args):
        if not callable(maybe_func) or iscoroutinefunction(maybe_func):
            msg = f"a green function was expected, got {maybe_func!r}"
            raise TypeError(msg)

        if seconds <= 0:
            callback = get_hub().loop.run_callback(getcurrent().throw, Timeout)

            try:
                return maybe_func(*args)
            finally:
                callback.close()

        return with_timeout(seconds, maybe_func, *args)

    return _gevent_timeout_after(seconds, maybe_func, *args)


@overload
def _asyncio_timeout_after(
    seconds: float,
    maybe_func: Awaitable[_T],
    /,
) -> Coroutine[Any, Any, _T]: ...
@overload
def _asyncio_timeout_after(
    seconds: float,
    maybe_func: Callable[[Unpack[_Ts]], _T],
    /,
    *args: Unpack[_Ts],
) -> _T: ...
def _asyncio_timeout_after(seconds, maybe_func, /, *args):
    from asyncio import wait_for

    if sys.version_info >= (3, 11):
        from asyncio import timeout

        async def _asyncio_timeout_after_for_coroutine_function(
            seconds: float,
            maybe_func: Callable[[Unpack[_Ts]], Coroutine[Any, Any, _T]],
            /,
            *args: Unpack[_Ts],
        ) -> _T:
            async with timeout(seconds):
                return await maybe_func(*args)

    else:
        from asyncio import create_task, get_running_loop

        async def _asyncio_timeout_after_for_coroutine_function(
            seconds: float,
            maybe_func: Callable[[Unpack[_Ts]], Coroutine[Any, Any, _T]],
            /,
            *args: Unpack[_Ts],
        ) -> _T:
            if seconds <= 0:
                task = create_task(maybe_func(*args))
                handle = get_running_loop().call_soon(task.cancel)

                try:
                    return await task
                except get_cancelled_exc_class() as exc:
                    raise get_timeout_exc_class() from exc
                finally:
                    handle.cancel()

            return await wait_for(maybe_func(*args), seconds)

    @replaces(globals())
    def _asyncio_timeout_after(seconds, maybe_func, /, *args):
        if isawaitable(maybe_func):
            return wait_for(maybe_func, seconds)

        if iscoroutinefunction(maybe_func):
            return _asyncio_timeout_after_for_coroutine_function(
                seconds,
                maybe_func,
                *args,
            )

        msg = (
            f"an awaitable object or coroutine function was expected,"
            f" got {maybe_func!r}"
        )
        raise TypeError(msg)

    return _asyncio_timeout_after(seconds, maybe_func, *args)


@overload
def _curio_timeout_after(
    seconds: float,
    maybe_func: Awaitable[_T],
    /,
) -> Coroutine[Any, Any, _T]: ...
@overload
def _curio_timeout_after(
    seconds: float,
    maybe_func: Callable[[Unpack[_Ts]], _T],
    /,
    *args: Unpack[_Ts],
) -> _T: ...
def _curio_timeout_after(seconds, maybe_func, /, *args):
    from curio import disable_cancellation, sleep, timeout_after

    async def _curio_timeout_after_for_awaitable(
        seconds: float,
        maybe_func: Awaitable[_T],
        /,
    ) -> _T:
        async with timeout_after(max(0, seconds)):
            return await maybe_func

    async def _curio_timeout_after_for_coroutine_function(
        seconds: float,
        maybe_func: Callable[[Unpack[_Ts]], Coroutine[Any, Any, _T]],
        /,
        *args: Unpack[_Ts],
    ) -> _T:
        if seconds <= 0:
            async with timeout_after(0):
                await disable_cancellation(sleep, 0)

                return await maybe_func(*args)

        return await timeout_after(seconds, maybe_func, *args)

    @replaces(globals())
    def _curio_timeout_after(seconds, maybe_func, /, *args):
        if isawaitable(maybe_func):
            return _curio_timeout_after_for_awaitable(seconds, maybe_func)

        if iscoroutinefunction(maybe_func):
            return _curio_timeout_after_for_coroutine_function(
                seconds,
                maybe_func,
                *args,
            )

        msg = (
            f"an awaitable object or coroutine function was expected,"
            f" got {maybe_func!r}"
        )
        raise TypeError(msg)

    return _curio_timeout_after(seconds, maybe_func, *args)


@overload
def _trio_timeout_after(
    seconds: float,
    maybe_func: Awaitable[_T],
    /,
) -> Coroutine[Any, Any, _T]: ...
@overload
def _trio_timeout_after(
    seconds: float,
    maybe_func: Callable[[Unpack[_Ts]], _T],
    /,
    *args: Unpack[_Ts],
) -> _T: ...
def _trio_timeout_after(seconds, maybe_func, /, *args):
    from trio import fail_after

    async def _trio_timeout_after_for_awaitable(
        seconds: float,
        maybe_func: Awaitable[_T],
        /,
    ) -> _T:
        with fail_after(max(0, seconds)):
            return await maybe_func

    async def _trio_timeout_after_for_coroutine_function(
        seconds: float,
        maybe_func: Callable[[Unpack[_Ts]], Coroutine[Any, Any, _T]],
        /,
        *args: Unpack[_Ts],
    ) -> _T:
        with fail_after(max(0, seconds)):
            return await maybe_func(*args)

    @replaces(globals())
    def _trio_timeout_after(seconds, maybe_func, /, *args):
        if isawaitable(maybe_func):
            return _trio_timeout_after_for_awaitable(seconds, maybe_func)

        if iscoroutinefunction(maybe_func):
            return _trio_timeout_after_for_coroutine_function(
                seconds,
                maybe_func,
                *args,
            )

        msg = (
            f"an awaitable object or coroutine function was expected,"
            f" got {maybe_func!r}"
        )
        raise TypeError(msg)

    return _trio_timeout_after(seconds, maybe_func, *args)


@overload
def _anyio_timeout_after(
    seconds: float,
    maybe_func: Awaitable[_T],
    /,
) -> Coroutine[Any, Any, _T]: ...
@overload
def _anyio_timeout_after(
    seconds: float,
    maybe_func: Callable[[Unpack[_Ts]], _T],
    /,
    *args: Unpack[_Ts],
) -> _T: ...
def _anyio_timeout_after(seconds, maybe_func, /, *args):
    from anyio import fail_after

    async def _anyio_timeout_after_for_awaitable(
        seconds: float,
        maybe_func: Awaitable[_T],
        /,
    ) -> _T:
        with fail_after(max(0, seconds)):
            return await maybe_func

    async def _anyio_timeout_after_for_coroutine_function(
        seconds: float,
        maybe_func: Callable[[Unpack[_Ts]], Coroutine[Any, Any, _T]],
        /,
        *args: Unpack[_Ts],
    ) -> _T:
        with fail_after(max(0, seconds)):
            return await maybe_func(*args)

    @replaces(globals())
    def _anyio_timeout_after(seconds, maybe_func, /, *args):
        if isawaitable(maybe_func):
            return _anyio_timeout_after_for_awaitable(seconds, maybe_func)

        if iscoroutinefunction(maybe_func):
            return _anyio_timeout_after_for_coroutine_function(
                seconds,
                maybe_func,
                *args,
            )

        msg = (
            f"an awaitable object or coroutine function was expected,"
            f" got {maybe_func!r}"
        )
        raise TypeError(msg)

    return _anyio_timeout_after(seconds, maybe_func, *args)


@overload
def timeout_after(
    seconds: float,
    maybe_func: Awaitable[_T],
    /,
    *,
    executor: TaskExecutor | DefaultType = DEFAULT,
) -> Coroutine[Any, Any, _T]: ...
@overload
def timeout_after(
    seconds: float,
    maybe_func: Callable[[Unpack[_Ts]], _T],
    /,
    *args: Unpack[_Ts],
    executor: TaskExecutor | DefaultType = DEFAULT,
) -> _T: ...
def timeout_after(seconds, maybe_func, /, *args, executor=DEFAULT):
    if executor is DEFAULT:
        executor = current_executor()

    library = executor.library

    if library == "threading":
        impl = _threading_timeout_after
    elif library == "eventlet":
        impl = _eventlet_timeout_after
    elif library == "gevent":
        impl = _gevent_timeout_after
    elif library == "asyncio":
        impl = _asyncio_timeout_after
    elif library == "curio":
        impl = _curio_timeout_after
    elif library == "trio":
        impl = _trio_timeout_after
    elif library == "anyio":
        impl = _anyio_timeout_after
    else:
        msg = f"unsupported library {library!r}"
        raise RuntimeError(msg)

    return impl(seconds, maybe_func, *args)
