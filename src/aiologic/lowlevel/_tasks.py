#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from inspect import isawaitable, iscoroutinefunction
from typing import Any, TypeVar

from wrapt import ObjectProxy, decorator, when_imported

from aiologic.meta import replaces

from ._libraries import current_async_library, current_green_library

if sys.version_info >= (3, 11):
    from typing import overload
else:
    from typing_extensions import overload

if sys.version_info >= (3, 9):
    from collections.abc import Awaitable, Callable
else:
    from typing import Awaitable, Callable

_AwaitableT = TypeVar("_AwaitableT", bound=Awaitable[Any])
_CallableT = TypeVar("_CallableT", bound=Callable[..., Any])
_T = TypeVar("_T")


@overload
def _eventlet_shielded_call(
    wrapped: Callable[[], _T],
    args: None,
    kwargs: None,
    /,
) -> _T: ...
@overload
def _eventlet_shielded_call(
    wrapped: Callable[..., _T],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    /,
) -> _T: ...
def _eventlet_shielded_call(wrapped, args, kwargs, /):
    from eventlet import Timeout, spawn
    from eventlet.hubs import get_hub
    from greenlet import GreenletExit, getcurrent

    @replaces(globals())
    def _eventlet_shielded_call(wrapped, args, kwargs, /):
        exc = None

        try:
            timeouts = []

            try:
                try:
                    if args is None:
                        wait = wrapped
                    else:
                        wait = spawn(wrapped, *args, **kwargs).wait

                    while True:
                        try:
                            result = wait()
                        except GreenletExit as e:
                            exc = e
                        except Timeout as timeout:
                            timeouts.append(timeout)
                        else:
                            break
                except BaseException as e:
                    exc = e
                    raise
                finally:
                    if timeouts:
                        if exc is None:
                            exc, *timeouts = timeouts

                        for timeout in timeouts:
                            if not timeout.pending:
                                timeout.timer = get_hub().schedule_call_global(
                                    0,
                                    getcurrent().throw,
                                    timeout,
                                )

                if exc is not None:
                    raise exc
            finally:
                del timeouts
        finally:
            del exc

        return result

    return _eventlet_shielded_call(wrapped, args, kwargs)


@overload
def _gevent_shielded_call(
    wrapped: Callable[[], _T],
    args: None,
    kwargs: None,
    /,
) -> _T: ...
@overload
def _gevent_shielded_call(
    wrapped: Callable[..., _T],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    /,
) -> _T: ...
def _gevent_shielded_call(wrapped, args, kwargs, /):
    from gevent import Timeout, get_hub, spawn
    from greenlet import GreenletExit, getcurrent

    @replaces(globals())
    def _gevent_shielded_call(wrapped, args, kwargs, /):
        exc = None

        try:
            timeouts = []

            try:
                try:
                    if args is None:
                        wait = wrapped
                    else:
                        wait = spawn(wrapped, *args, **kwargs).get

                    while True:
                        try:
                            result = wait()
                        except GreenletExit as e:
                            exc = e
                        except Timeout as timeout:
                            timeouts.append(timeout)
                        else:
                            break
                except BaseException as e:
                    exc = e
                    raise
                finally:
                    if timeouts:
                        if exc is None:
                            exc, *timeouts = timeouts

                        for timeout in timeouts:
                            if not timeout.pending:
                                timeout.timer.close()
                                timeout.timer = get_hub().loop.run_callback(
                                    getcurrent().throw,
                                    timeout,
                                )

                if exc is not None:
                    raise exc
            finally:
                del timeouts
        finally:
            del exc

        return result

    return _gevent_shielded_call(wrapped, args, kwargs)


@overload
async def _asyncio_shielded_call(
    wrapped: Awaitable[_T],
    args: None,
    kwargs: None,
    /,
) -> _T: ...
@overload
async def _asyncio_shielded_call(
    wrapped: Callable[..., Awaitable[_T]],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    /,
) -> _T: ...
async def _asyncio_shielded_call(wrapped, args, kwargs, /):
    from asyncio import CancelledError, ensure_future, shield

    @replaces(globals())
    async def _asyncio_shielded_call(wrapped, args, kwargs, /):
        exc = None

        try:
            if args is None:
                future = ensure_future(wrapped)
            else:
                future = ensure_future(wrapped(*args, **kwargs))

            while True:
                try:
                    result = await shield(future)
                except CancelledError as e:
                    exc = e
                else:
                    break

            if exc is not None:
                raise exc
        finally:
            del exc

        return result

    return await _asyncio_shielded_call(wrapped, args, kwargs)


@when_imported("anyio")
def _(_):
    @replaces(globals())
    async def _asyncio_shielded_call(wrapped, args, kwargs, /):
        from asyncio import CancelledError, ensure_future, shield

        from anyio import CancelScope

        @replaces(globals())
        async def _asyncio_shielded_call(wrapped, args, kwargs, /):
            with CancelScope(shield=True):
                exc = None

                try:
                    if args is None:
                        future = ensure_future(wrapped)
                    else:
                        future = ensure_future(wrapped(*args, **kwargs))

                    while True:
                        try:
                            result = await shield(future)
                        except CancelledError as e:
                            exc = e
                        else:
                            break

                    if exc is not None:
                        raise exc
                finally:
                    del exc

            return result

        return await _asyncio_shielded_call(wrapped, args, kwargs)


@overload
async def _curio_shielded_call(
    wrapped: Awaitable[_T],
    args: None,
    kwargs: None,
    /,
) -> _T: ...
@overload
async def _curio_shielded_call(
    wrapped: Callable[..., Awaitable[_T]],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    /,
) -> _T: ...
async def _curio_shielded_call(wrapped, args, kwargs, /):
    from curio import disable_cancellation

    @replaces(globals())
    async def _curio_shielded_call(wrapped, args, kwargs, /):
        async with disable_cancellation():
            if args is None:
                return await wrapped
            else:
                return await wrapped(*args, **kwargs)

    return await _curio_shielded_call(wrapped, args, kwargs)


@overload
async def _trio_shielded_call(
    wrapped: Awaitable[_T],
    args: None,
    kwargs: None,
    /,
) -> _T: ...
@overload
async def _trio_shielded_call(
    wrapped: Callable[..., Awaitable[_T]],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    /,
) -> _T: ...
async def _trio_shielded_call(wrapped, args, kwargs, /):
    from trio import CancelScope

    @replaces(globals())
    async def _trio_shielded_call(wrapped, args, kwargs, /):
        with CancelScope(shield=True):
            if args is None:
                return await wrapped
            else:
                return await wrapped(*args, **kwargs)

    return await _trio_shielded_call(wrapped, args, kwargs)


@decorator
def __green_shield(wrapped, instance, args, kwargs, /):
    library = current_green_library()

    if library == "threading":
        return wrapped(*args, **kwargs)

    if library == "eventlet":
        return _eventlet_shielded_call(wrapped, args, kwargs)

    if library == "gevent":
        return _gevent_shielded_call(wrapped, args, kwargs)

    msg = f"unsupported green library {library!r}"
    raise RuntimeError(msg)


@decorator
async def __async_shield(wrapped, instance, args, kwargs, /):
    library = current_async_library()

    if library == "asyncio":
        return await _asyncio_shielded_call(wrapped, args, kwargs)

    if library == "curio":
        return await _curio_shielded_call(wrapped, args, kwargs)

    if library == "trio":
        return await _trio_shielded_call(wrapped, args, kwargs)

    msg = f"unsupported async library {library!r}"
    raise RuntimeError(msg)


class __ShieldedAwaitable(ObjectProxy):
    __slots__ = ()

    def __await__(self, /):
        library = current_async_library()

        if library == "asyncio":
            coro = _asyncio_shielded_call(self.__wrapped__, None, None)
        elif library == "curio":
            coro = _curio_shielded_call(self.__wrapped__, None, None)
        elif library == "trio":
            coro = _trio_shielded_call(self.__wrapped__, None, None)
        else:
            msg = f"unsupported async library {library!r}"
            raise RuntimeError(msg)

        try:
            return (yield from coro.__await__())
        except BaseException:
            self = None  # noqa: PLW0642
            raise


@overload
def shield(wrapped: _AwaitableT, /) -> _AwaitableT: ...
@overload
def shield(wrapped: _CallableT, /) -> _CallableT: ...
def shield(wrapped, /):
    """..."""

    if isawaitable(wrapped):
        return __ShieldedAwaitable(wrapped)

    if iscoroutinefunction(wrapped):
        return __async_shield(wrapped)

    return __green_shield(wrapped)
