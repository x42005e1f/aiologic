#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from inspect import isawaitable, iscoroutinefunction

from wrapt import decorator, when_imported

from ._libraries import current_async_library, current_green_library


def _eventlet_shield(wrapped, args, kwargs, /):
    global _eventlet_shield

    from eventlet import Timeout, spawn
    from eventlet.greenthread import GreenThread
    from eventlet.hubs import get_hub
    from greenlet import GreenletExit, getcurrent

    def _eventlet_shield(wrapped, args, kwargs, /):
        exc = None

        try:
            timeouts = []

            try:
                try:
                    if args is None:
                        if isinstance(wrapped, GreenThread):
                            wait = wrapped.wait
                        else:
                            wait = wrapped.switch
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

    return _eventlet_shield(wrapped, args, kwargs)


def _gevent_shield(wrapped, args, kwargs, /):
    global _gevent_shield

    from gevent import Greenlet, Timeout, get_hub, spawn
    from greenlet import GreenletExit, getcurrent

    def _gevent_shield(wrapped, args, kwargs, /):
        exc = None

        try:
            timeouts = []

            try:
                try:
                    if args is None:
                        if isinstance(wrapped, Greenlet):
                            wait = wrapped.get
                        else:
                            wait = wrapped.switch
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

    return _gevent_shield(wrapped, args, kwargs)


async def _asyncio_shield(wrapped, args, kwargs, /):
    global _asyncio_shield

    from asyncio import CancelledError, ensure_future, shield

    async def _asyncio_shield(wrapped, args, kwargs, /):
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

    return await _asyncio_shield(wrapped, args, kwargs)


@when_imported("anyio")
def _asyncio_shield_hook(_):
    global _asyncio_shield

    async def _asyncio_shield(wrapped, args, kwargs, /):
        global _asyncio_shield

        from asyncio import CancelledError, ensure_future, shield

        from anyio import CancelScope

        async def _asyncio_shield(wrapped, args, kwargs, /):
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

        return await _asyncio_shield(wrapped, args, kwargs)


async def _curio_shield(wrapped, args, kwargs, /):
    global _curio_shield

    from curio import disable_cancellation

    async def _curio_shield(wrapped, args, kwargs, /):
        async with disable_cancellation():
            if args is None:
                return await wrapped
            else:
                return await wrapped(*args, **kwargs)

    return await _curio_shield(wrapped, args, kwargs)


async def _trio_shield(wrapped, args, kwargs, /):
    global _trio_shield

    from trio import CancelScope

    async def _trio_shield(wrapped, args, kwargs, /):
        with CancelScope(shield=True):
            if args is None:
                return await wrapped
            else:
                return await wrapped(*args, **kwargs)

    return await _trio_shield(wrapped, args, kwargs)


@decorator
def _green_shield(wrapped, instance, args, kwargs, /):
    library = current_green_library()

    if library == "threading":
        return wrapped(*args, **kwargs)
    elif library == "eventlet":
        return _eventlet_shield(wrapped, args, kwargs)
    elif library == "gevent":
        return _gevent_shield(wrapped, args, kwargs)
    else:
        msg = f"unsupported green library {library!r}"
        raise RuntimeError(msg)


@decorator
async def _async_shield(wrapped, instance, args, kwargs, /):
    library = current_async_library()

    if library == "asyncio":
        return await _asyncio_shield(wrapped, args, kwargs)
    elif library == "curio":
        return await _curio_shield(wrapped, args, kwargs)
    elif library == "trio":
        return await _trio_shield(wrapped, args, kwargs)
    else:
        msg = f"unsupported async library {library!r}"
        raise RuntimeError(msg)


async def _async_shield_for_awaitable(wrapped, /):
    library = current_async_library()

    if library == "asyncio":
        return await _asyncio_shield(wrapped, None, None)
    elif library == "curio":
        return await _curio_shield(wrapped, None, None)
    elif library == "trio":
        return await _trio_shield(wrapped, None, None)
    else:
        msg = f"unsupported async library {library!r}"
        raise RuntimeError(msg)


def shield(wrapped, /):
    if isawaitable(wrapped):
        return _async_shield_for_awaitable(wrapped)
    elif iscoroutinefunction(wrapped):
        return _async_shield(wrapped)
    else:
        return _green_shield(wrapped)
