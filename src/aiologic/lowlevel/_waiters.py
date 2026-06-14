#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from math import inf, isinf, isnan
from typing import TYPE_CHECKING, Any, Literal, NoReturn, Protocol, final

from aiologic.meta import copies, generator

from ._libraries import current_async_library, current_green_library
from ._locks import once
from ._safety import signal_safety_enabled

if TYPE_CHECKING:
    if sys.version_info >= (3, 9):
        from collections.abc import Callable
    else:
        from typing import Callable


class Waiter(Protocol):
    """
    The simplest synchronization primitive.

    It represents a blocking call that can either be completed from outside by
    a task/thread or be cancelled (due to a timeout or an exception). One wait
    is one instance.

    Unlike all other primitives, it is bound to the current event loop upon
    creation.
    """

    __slots__ = ()

    def wake(self, /) -> None:
        """
        Reschedule (resume/notify) the task that is blocked.

        It can be called multiple times and in parallel: all calls are expected
        to be serialized by the event loop (if any). If no task is blocked on
        the primitive, it has no effect.

        Note that while redundant calls are allowed, they can lead to excessive
        load on the event loop in the form of callback flood. If your scenario
        involves either multiple notifiers or premature task rescheduling
        (e.g., due to a timeout), consider using events instead of waiters.
        """


class GreenWaiter(Waiter, Protocol):
    """
    The return type of :func:`create_green_waiter`.
    """

    __slots__ = ()

    def wait(self, /, timeout: float | None = None) -> bool:
        """
        Block (put to sleep) the task until :meth:`wake` is called from any
        thread, and then return :data:`True`.

        It must be called exactly once (or never) during the object's lifetime,
        even if the first call was cancelled due to a timeout. Otherwise, the
        behavior is undefined.

        Args:
          timeout:
            If set to a non-negative number, the method will block at most
            *timeout* seconds and return :data:`False` if there were no calls
            to :meth:`wake` within that time. For zero: if no such calls were
            serialized.
        """

    def wake(self, /) -> None:
        """
        Reschedule (resume/notify) the task that is blocked.

        It can be called multiple times and in parallel: all calls are expected
        to be serialized by the event loop (if any). If no task is blocked on
        the primitive, it has no effect.

        Note that while redundant calls are allowed, they can lead to excessive
        load on the event loop in the form of callback flood. If your scenario
        involves either multiple notifiers or premature task rescheduling
        (e.g., due to a timeout), consider using events instead of waiters.
        """

    @property
    def shield(self, /) -> bool:
        """
        A boolean that is :data:`True` if the :meth:`wait` call will be
        shielded from external cancellation, :data:`False` otherwise.

        The effect is mostly equivalent to applying the :func:`shield`
        universal decorator to the method, but it is more efficient. Also, any
        non-negative timeout passed to the method will be ignored.

        It can be rewritten, but any changes will only take effect until the
        call.
        """

    @shield.setter
    def shield(self, /, value: bool) -> None: ...


class AsyncWaiter(Waiter, Protocol):
    """
    The return type of :func:`create_async_waiter`.
    """

    __slots__ = ()

    @generator
    async def __await__(self, /, timeout: float | None = None) -> bool:
        """
        Block (put to sleep) the task until :meth:`wake` is called from any
        thread, and then return :data:`True`.

        It must be called exactly once (or never) during the object's lifetime,
        even if the first call was cancelled due to a timeout. Otherwise, the
        behavior is undefined.

        Used by the :keyword:`await` expressions.

        Args:
          timeout:
            If set to a non-negative number, the method will block at most
            *timeout* seconds and return :data:`False` if there were no calls
            to :meth:`wake` within that time. For zero: if no such calls were
            serialized.
        """

    async def with_(self, /, timeout: float | None = None) -> bool:
        """
        Block (put to sleep) the task until :meth:`wake` is called from any
        thread, and then return :data:`True`.

        It must be called exactly once (or never) during the object's lifetime,
        even if the first call was cancelled due to a timeout. Otherwise, the
        behavior is undefined.

        Args:
          timeout:
            If set to a non-negative number, the method will block at most
            *timeout* seconds and return :data:`False` if there were no calls
            to :meth:`wake` within that time. For zero: if no such calls were
            serialized.
        """

    def wake(self, /) -> None:
        """
        Reschedule (resume/notify) the task that is blocked.

        It can be called multiple times and in parallel: all calls are expected
        to be serialized by the event loop (if any). If no task is blocked on
        the primitive, it has no effect.

        Note that while redundant calls are allowed, they can lead to excessive
        load on the event loop in the form of callback flood. If your scenario
        involves either multiple notifiers or premature task rescheduling
        (e.g., due to a timeout), consider using events instead of waiters.
        """

    @property
    def shield(self, /) -> bool:
        """
        A boolean that is :data:`True` if the :meth:`__await__`/:meth:`with_`
        call will be shielded from external cancellation, :data:`False`
        otherwise.

        The effect is mostly equivalent to applying the :func:`shield`
        universal decorator to the primitive/method, but it is more efficient.
        Also, any non-negative timeout passed to the method will be ignored.

        It can be rewritten, but any changes will only take effect until the
        call.
        """

    @shield.setter
    def shield(self, /, value: bool) -> None: ...


@once(reentrant=True)
def _get_threading_waiter_class() -> type[GreenWaiter]:
    from . import _time
    from ._locks import create_thread_lock

    @final
    class _ThreadingWaiter(GreenWaiter):
        __slots__ = (
            "__lock",
            "shield",
        )

        shield: bool

        def __init__(self, /, shield: bool = False) -> None:
            self.__lock = create_thread_lock()
            self.__lock.acquire()

            self.shield = shield

        def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn:
            bcs = _ThreadingWaiter
            bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

            msg = f"type '{bcs_repr}' is not an acceptable base type"
            raise TypeError(msg)

        def __reduce__(self, /) -> NoReturn:
            msg = f"cannot reduce {self!r}"
            raise TypeError(msg)

        def wait(self, /, timeout: float | None = None) -> bool:
            if timeout is not None:
                if isinstance(timeout, int):
                    try:
                        timeout = float(timeout)
                    except OverflowError:
                        timeout = (-1 if timeout < 0 else +1) * inf

                if isnan(timeout):
                    msg = "timeout must be non-NaN"
                    raise ValueError(msg)

                if timeout < 0:
                    msg = "timeout must be non-negative"
                    raise ValueError(msg)

                if isinf(timeout):
                    timeout = None

            if timeout is None or self.shield:
                return self.__lock.acquire()
            elif timeout:
                return _time._green_long_sleep(
                    self.__wait_with_timeout,
                    timeout,
                    _time._threading_seconds_per_timeout(),
                    clock=_time._threading_clock,
                    check=True,
                )
            else:
                return self.__wait_with_zero()

        def __wait_with_timeout(self, /, timeout: float) -> bool:
            return self.__lock.acquire(True, timeout)

        def __wait_with_zero(self, /) -> bool:
            return self.__lock.acquire(False)

        def wake(self, /) -> None:
            try:
                self.__lock.release()
            except RuntimeError:  # unlocked
                pass

    return _ThreadingWaiter


@once
def _get_eventlet_waiter_class() -> type[GreenWaiter]:
    from eventlet.hubs import _threadlocal, get_hub
    from greenlet import getcurrent

    from aiologic._monkey import patch_eventlet

    from . import _tasks, _time

    patch_eventlet()

    @final
    class _EventletWaiter(GreenWaiter):
        __slots__ = (
            "__greenlet",
            "__hub",
            "shield",
        )

        shield: bool

        def __init__(self, /, shield: bool = False) -> None:
            self.__greenlet = None
            self.__hub = get_hub()

            self.shield = shield

        def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn:
            bcs = _EventletWaiter
            bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

            msg = f"type '{bcs_repr}' is not an acceptable base type"
            raise TypeError(msg)

        def __reduce__(self, /) -> NoReturn:
            msg = f"cannot reduce {self!r}"
            raise TypeError(msg)

        def wait(self, /, timeout: float | None = None) -> bool:
            if timeout is not None:
                if isinstance(timeout, int):
                    try:
                        timeout = float(timeout)
                    except OverflowError:
                        timeout = (-1 if timeout < 0 else +1) * inf

                if isnan(timeout):
                    msg = "timeout must be non-NaN"
                    raise ValueError(msg)

                if timeout < 0:
                    msg = "timeout must be non-negative"
                    raise ValueError(msg)

                if isinf(timeout):
                    timeout = None

            self.__greenlet = getcurrent()

            try:
                if self.__hub.greenlet is self.__greenlet:
                    msg = "do not call blocking functions from the mainloop"
                    raise RuntimeError(msg)

                if timeout is None or self.shield:
                    if self.shield:
                        return _tasks._eventlet_shielded_call(
                            self.__hub.switch,
                            None,
                            None,
                        )
                    else:
                        return self.__hub.switch()
                elif timeout:
                    return _time._green_long_sleep(
                        self.__wait_with_timeout,
                        timeout,
                        _time._eventlet_seconds_per_timeout(),
                        clock=_time._eventlet_clock,
                        check=True,
                    )
                else:
                    return self.__wait_with_zero()
            finally:
                self.__greenlet = None

        def __wait_with_timeout(self, /, timeout: float) -> bool:
            timer = self.__hub.schedule_call_global(
                timeout,
                self.__notify,
                False,
            )

            try:
                return self.__hub.switch()
            finally:
                timer.cancel()

        def __wait_with_zero(self, /) -> bool:
            timer = self.__hub.schedule_call_global(0, self.__notify, False)

            try:
                return self.__hub.switch()
            finally:
                timer.cancel()

        def __notify(self, /, result: bool = True) -> None:
            if self.__greenlet is not None:
                self.__greenlet.switch(result)

        def wake(self, /) -> None:
            current_hub = getattr(_threadlocal, "hub", None)

            if current_hub is self.__hub and not signal_safety_enabled():
                self.__hub.schedule_call_global(0, self.__notify)
            else:
                self.__hub.schedule_call_threadsafe(0, self.__notify)

    return _EventletWaiter


@once
def _get_gevent_waiter_class() -> type[GreenWaiter]:
    from gevent import get_hub
    from gevent._hub_local import get_hub_if_exists
    from greenlet import getcurrent

    from . import _tasks, _time

    def _noop() -> None:
        pass

    @final
    class _GeventWaiter(GreenWaiter):
        __slots__ = (
            "__greenlet",
            "__hub",
            "shield",
        )

        shield: bool

        def __init__(self, /, shield: bool = False) -> None:
            self.__greenlet = None
            self.__hub = get_hub()

            self.shield = shield

        def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn:
            bcs = _GeventWaiter
            bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

            msg = f"type '{bcs_repr}' is not an acceptable base type"
            raise TypeError(msg)

        def __reduce__(self, /) -> NoReturn:
            msg = f"cannot reduce {self!r}"
            raise TypeError(msg)

        def wait(self, /, timeout: float | None = None) -> bool:
            if timeout is not None:
                if isinstance(timeout, int):
                    try:
                        timeout = float(timeout)
                    except OverflowError:
                        timeout = (-1 if timeout < 0 else +1) * inf

                if isnan(timeout):
                    msg = "timeout must be non-NaN"
                    raise ValueError(msg)

                if timeout < 0:
                    msg = "timeout must be non-negative"
                    raise ValueError(msg)

                if isinf(timeout):
                    timeout = None

            self.__greenlet = getcurrent()

            try:
                if self.__hub is self.__greenlet:
                    msg = "do not call blocking functions from the mainloop"
                    raise RuntimeError(msg)

                if timeout is None or self.shield:
                    watcher = self.__hub.loop.async_()
                    watcher.start(_noop)  # avoid LoopExit

                    try:
                        if self.shield:
                            return _tasks._gevent_shielded_call(
                                self.__hub.switch,
                                None,
                                None,
                            )
                        else:
                            return self.__hub.switch()
                    finally:
                        watcher.close()
                elif timeout:
                    return _time._green_long_sleep(
                        self.__wait_with_timeout,
                        timeout,
                        _time._gevent_seconds_per_timeout(),
                        clock=_time._gevent_clock,
                        check=True,
                    )
                else:
                    return self.__wait_with_zero()
            finally:
                self.__greenlet = None

        def __wait_with_timeout(self, /, timeout: float) -> bool:
            timer = self.__hub.loop.timer(timeout)
            timer.start(self.__notify, False, update=True)

            try:
                return self.__hub.switch()
            finally:
                timer.close()

        def __wait_with_zero(self, /) -> bool:
            callback = self.__hub.loop.run_callback(self.__notify, False)

            try:
                return self.__hub.switch()
            finally:
                callback.close()

        def __notify(self, /, result: bool = True) -> None:
            if self.__greenlet is not None:
                switch = self.__greenlet.switch

                try:
                    switch(result)
                except BaseException:  # noqa: BLE001
                    self.__hub.handle_error(switch, *sys.exc_info())

        def wake(self, /) -> None:
            current_hub = get_hub_if_exists()

            try:
                if current_hub is self.__hub and not signal_safety_enabled():
                    self.__hub.loop.run_callback(self.__notify)
                else:
                    self.__hub.loop.run_callback_threadsafe(self.__notify)
            except ValueError:  # event loop is destroyed
                pass

    return _GeventWaiter


@once
def _get_asyncio_waiter_class() -> type[AsyncWaiter]:
    from asyncio import (
        InvalidStateError,
        _get_running_loop as get_running_loop_if_exists,
        get_running_loop,
    )

    from . import _tasks, _time

    @final
    class _AsyncioWaiter(AsyncWaiter):
        __slots__ = (
            "__future",
            "__loop",
            "shield",
        )

        shield: bool

        def __init__(self, /, shield: bool = False) -> None:
            self.__future = None
            self.__loop = get_running_loop()

            self.shield = shield

        def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn:
            bcs = _AsyncioWaiter
            bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

            msg = f"type '{bcs_repr}' is not an acceptable base type"
            raise TypeError(msg)

        def __reduce__(self, /) -> NoReturn:
            msg = f"cannot reduce {self!r}"
            raise TypeError(msg)

        async def __await(self, /, timeout: float | None = None) -> bool:
            if timeout is not None:
                if isinstance(timeout, int):
                    try:
                        timeout = float(timeout)
                    except OverflowError:
                        timeout = (-1 if timeout < 0 else +1) * inf

                if isnan(timeout):
                    msg = "timeout must be non-NaN"
                    raise ValueError(msg)

                if timeout < 0:
                    msg = "timeout must be non-negative"
                    raise ValueError(msg)

                if isinf(timeout):
                    timeout = None

            self.__future = self.__loop.create_future()

            try:
                if timeout is None or self.shield:
                    if self.shield:
                        return await _tasks._asyncio_shielded_call(
                            self.__future,
                            None,
                            None,
                        )
                    else:
                        return await self.__future
                elif timeout:
                    return await _time._async_long_sleep(
                        self.__wait_with_timeout,
                        timeout,
                        _time._asyncio_seconds_per_timeout(),
                        clock=_time._asyncio_clock,
                        check=True,
                    )
                else:
                    return await self.__wait_with_zero()
            finally:
                self.__future = None

        @generator
        @copies(__await)
        async def __await__(self, /, timeout: float | None = None) -> bool:
            return await self.__await(timeout)

        @copies(__await)
        async def with_(self, /, timeout: float | None = None) -> bool:
            return await self.__await(timeout)

        async def __wait_with_timeout(self, /, timeout: float) -> bool:
            handle = self.__loop.call_later(timeout, self.__notify, False)
            try:
                return await self.__future
            finally:
                handle.cancel()

        async def __wait_with_zero(self, /) -> bool:
            handle = self.__loop.call_soon(self.__notify, False)
            try:
                return await self.__future
            finally:
                handle.cancel()

        def __notify(self, /, result: bool = True) -> None:
            if self.__future is not None:
                try:
                    self.__future.set_result(result)
                except InvalidStateError:  # task is cancelled
                    pass

                self.__future = None

        def wake(self, /) -> None:
            current_loop = get_running_loop_if_exists()

            if current_loop is self.__loop and not signal_safety_enabled():
                self.__notify()
            else:
                try:
                    self.__loop.call_soon_threadsafe(self.__notify)
                except RuntimeError:  # event loop is closed
                    pass

    return _AsyncioWaiter


@once
def _get_curio_waiter_class() -> type[AsyncWaiter]:
    import sys

    from concurrent.futures import CancelledError, InvalidStateError
    from logging import getLogger

    from curio import check_cancellation, ignore_after
    from curio.traps import _future_wait

    from . import _tasks, _time

    if sys.version_info >= (3, 11):
        WaitTimeout = TimeoutError
    else:
        from concurrent.futures import TimeoutError as WaitTimeout

    _LOGGER = getLogger("concurrent.futures")

    class _CurioFuture:
        __slots__ = (
            "__weakref__",
            "_cancelled",
            "_done_callbacks",
            "_exception",
            "_pending",
            "_result",
        )

        def __init__(self, /) -> None:
            self._cancelled = True
            self._done_callbacks = []
            self._pending = [None]

        def cancel(self) -> bool:
            if self._pending:
                try:
                    self._pending.pop()
                except IndexError:
                    pass
                else:
                    self._cancelled = True

                    self._invoke_callbacks()

            return self._cancelled

        def cancelled(self) -> bool:
            return self._cancelled

        def running(self) -> bool:
            return False

        def done(self) -> bool:
            return not self._pending

        def result(self, timeout: float | None = None) -> bool:
            if not self._pending:
                if not self._cancelled:
                    try:
                        return self._result
                    except AttributeError:
                        pass

                raise CancelledError

            if timeout is not None and timeout <= 0:
                raise WaitTimeout

            raise NotImplementedError

        def exception(
            self,
            timeout: float | None = None,
        ) -> BaseException | None:
            if not self._pending:
                if not self._cancelled:
                    try:
                        return self._exception
                    except AttributeError:
                        pass

                raise CancelledError

            if timeout is not None and timeout <= 0:
                raise WaitTimeout

            raise NotImplementedError

        def add_done_callback(
            self,
            fn: Callable[[_CurioFuture], object],
        ) -> None:
            if not self._pending:
                try:
                    fn(self)
                except Exception:
                    _LOGGER.exception(
                        "exception calling callback for %r",
                        self,
                    )

                return

            self._done_callbacks.append(fn)

            if not self._pending:
                try:
                    self._done_callbacks.remove(fn)
                except ValueError:
                    pass
                else:
                    try:
                        fn(self)
                    except Exception:
                        _LOGGER.exception(
                            "exception calling callback for %r",
                            self,
                        )

        def set_running_or_notify_cancel(self) -> bool:
            raise NotImplementedError

        def set_result(self, result: bool) -> None:
            self._exception = None
            self._result = result

            if self._pending:
                try:
                    self._pending.pop()
                except IndexError:
                    pass
                else:
                    self._invoke_callbacks()
                    return

            raise InvalidStateError

        def set_exception(self, exception: BaseException | None) -> None:
            raise NotImplementedError

        def _invoke_callbacks(self) -> None:
            callbacks = self._done_callbacks
            callbacks.reverse()

            while callbacks:
                try:
                    callback = callbacks.pop()
                except IndexError:
                    break
                else:
                    try:
                        callback(self)
                    except Exception:
                        _LOGGER.exception(
                            "exception calling callback for %r",
                            self,
                        )

    @final
    class _CurioWaiter(AsyncWaiter):
        __slots__ = (
            "__future",
            "shield",
        )

        shield: bool

        def __init__(self, /, shield: bool = False) -> None:
            self.__future = _CurioFuture()

            self.shield = shield

        def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn:
            bcs = _CurioWaiter
            bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

            msg = f"type '{bcs_repr}' is not an acceptable base type"
            raise TypeError(msg)

        def __reduce__(self, /) -> NoReturn:
            msg = f"cannot reduce {self!r}"
            raise TypeError(msg)

        async def __await(self, /, timeout: float | None = None) -> bool:
            if timeout is not None:
                if isinstance(timeout, int):
                    try:
                        timeout = float(timeout)
                    except OverflowError:
                        timeout = (-1 if timeout < 0 else +1) * inf

                if isnan(timeout):
                    msg = "timeout must be non-NaN"
                    raise ValueError(msg)

                if timeout < 0:
                    msg = "timeout must be non-negative"
                    raise ValueError(msg)

                if isinf(timeout):
                    timeout = None

            if timeout is None or self.shield:
                if self.shield:
                    await _tasks._curio_shielded_call(
                        _future_wait,
                        [self.__future],
                        {},
                    )
                    await check_cancellation()
                    return True
                else:
                    await _future_wait(self.__future)
                    return True
            elif timeout:
                return await _time._async_long_sleep(
                    self.__wait_with_timeout,
                    timeout,
                    _time._curio_seconds_per_timeout(),
                    clock=_time._curio_clock,
                    check=True,
                )
            else:
                return await self.__wait_with_zero()

        @generator
        @copies(__await)
        async def __await__(self, /, timeout: float | None = None) -> bool:
            return await self.__await(timeout)

        @copies(__await)
        async def with_(self, /, timeout: float | None = None) -> bool:
            return await self.__await(timeout)

        async def __wait_with_timeout(self, /, timeout: float) -> bool:
            if self.__future.done():
                await _future_wait(self.__future)

                return True

            async with ignore_after(timeout):
                await _future_wait(self.__future)

                return True

            return False

        async def __wait_with_zero(self, /) -> bool:
            if self.__future.done():
                await _future_wait(self.__future)

                return True

            async with ignore_after(0):
                await _future_wait(self.__future)

                return True

            return False

        def wake(self, /) -> None:
            try:
                self.__future.set_result(True)
            except InvalidStateError:  # future is cancelled
                pass

    return _CurioWaiter


@once
def _get_trio_waiter_class() -> type[AsyncWaiter]:
    from trio import CancelScope, RunFinishedError
    from trio.lowlevel import (
        Abort,
        current_task,
        current_trio_token,
        reschedule,
        wait_task_rescheduled,
    )

    from . import _tasks, _time

    @final
    class _TrioWaiter(AsyncWaiter):
        __slots__ = (
            "__task",
            "__token",
            "shield",
        )

        shield: bool

        def __init__(self, /, shield: bool = False) -> None:
            self.__task = None
            self.__token = current_trio_token()

            self.shield = shield

        def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn:
            bcs = _TrioWaiter
            bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

            msg = f"type '{bcs_repr}' is not an acceptable base type"
            raise TypeError(msg)

        def __reduce__(self, /) -> NoReturn:
            msg = f"cannot reduce {self!r}"
            raise TypeError(msg)

        async def __await(self, /, timeout: float | None = None) -> bool:
            if timeout is not None:
                if isinstance(timeout, int):
                    try:
                        timeout = float(timeout)
                    except OverflowError:
                        timeout = (-1 if timeout < 0 else +1) * inf

                if isnan(timeout):
                    msg = "timeout must be non-NaN"
                    raise ValueError(msg)

                if timeout < 0:
                    msg = "timeout must be non-negative"
                    raise ValueError(msg)

                if isinf(timeout):
                    timeout = None

            self.__task = current_task()

            try:
                if timeout is None or self.shield:
                    if self.shield:
                        await _tasks._trio_shielded_call(
                            wait_task_rescheduled,
                            [self.__abort],
                            {},
                        )
                        return True
                    else:
                        await wait_task_rescheduled(self.__abort)
                        return True
                elif timeout:
                    return await _time._async_long_sleep(
                        self.__wait_with_timeout,
                        timeout,
                        _time._trio_seconds_per_timeout(),
                        clock=_time._trio_clock,
                        check=True,
                    )
                else:
                    return await self.__wait_with_zero()
            finally:
                self.__task = None

        @generator
        @copies(__await)
        async def __await__(self, /, timeout: float | None = None) -> bool:
            return await self.__await(timeout)

        @copies(__await)
        async def with_(self, /, timeout: float | None = None) -> bool:
            return await self.__await(timeout)

        def __abort(self, /, raise_cancel: Any) -> Literal[Abort.SUCCEEDED]:
            self.__task = None

            return Abort.SUCCEEDED

        async def __wait_with_timeout(self, /, timeout: float) -> bool:
            with CancelScope() as scope:
                self.__token.run_sync_soon(
                    setattr,
                    scope,
                    "deadline",
                    _time._trio_clock() + timeout,
                )

                await wait_task_rescheduled(self.__abort)

                return True

            return False

        async def __wait_with_zero(self, /) -> bool:
            with CancelScope() as scope:
                self.__token.run_sync_soon(scope.cancel)

                await wait_task_rescheduled(self.__abort)

                return True

            return False

        def __notify(self, /) -> None:
            if self.__task is not None:
                reschedule(self.__task)

                self.__task = None

        def wake(self, /) -> None:
            try:
                current_token = current_trio_token()
            except RuntimeError:  # no called trio.run()
                current_token = None

            if current_token is self.__token and not signal_safety_enabled():
                self.__notify()
            else:
                try:
                    self.__token.run_sync_soon(self.__notify)
                except RunFinishedError:  # trio.run() is finished
                    pass

    return _TrioWaiter


def _create_threading_waiter(shield: bool = False) -> GreenWaiter:
    global _create_threading_waiter

    _create_threading_waiter = _get_threading_waiter_class()

    return _create_threading_waiter(shield=shield)


def _create_eventlet_waiter(shield: bool = False) -> GreenWaiter:
    global _create_eventlet_waiter

    _create_eventlet_waiter = _get_eventlet_waiter_class()

    return _create_eventlet_waiter(shield=shield)


def _create_gevent_waiter(shield: bool = False) -> GreenWaiter:
    global _create_gevent_waiter

    _create_gevent_waiter = _get_gevent_waiter_class()

    return _create_gevent_waiter(shield=shield)


def _create_asyncio_waiter(shield: bool = False) -> AsyncWaiter:
    global _create_asyncio_waiter

    _create_asyncio_waiter = _get_asyncio_waiter_class()

    return _create_asyncio_waiter(shield=shield)


def _create_curio_waiter(shield: bool = False) -> AsyncWaiter:
    global _create_curio_waiter

    _create_curio_waiter = _get_curio_waiter_class()

    return _create_curio_waiter(shield=shield)


def _create_trio_waiter(shield: bool = False) -> AsyncWaiter:
    global _create_trio_waiter

    _create_trio_waiter = _get_trio_waiter_class()

    return _create_trio_waiter(shield=shield)


def create_green_waiter(*, shield: bool = False) -> GreenWaiter:
    """
    Create a new instance for a blocking green call.

    Args:
      shield:
        See the :attr:`~GreenWaiter.shield` property.
    """

    library = current_green_library()

    if library == "threading":
        return _create_threading_waiter(shield)

    if library == "eventlet":
        return _create_eventlet_waiter(shield)

    if library == "gevent":
        return _create_gevent_waiter(shield)

    msg = f"unsupported green library {library!r}"
    raise RuntimeError(msg)


def create_async_waiter(*, shield: bool = False) -> AsyncWaiter:
    """
    Create a new instance for a blocking async call.

    Args:
      shield:
        See the :attr:`~AsyncWaiter.shield` property.
    """

    library = current_async_library()

    if library == "asyncio":
        return _create_asyncio_waiter(shield)

    if library == "curio":
        return _create_curio_waiter(shield)

    if library == "trio":
        return _create_trio_waiter(shield)

    msg = f"unsupported async library {library!r}"
    raise RuntimeError(msg)
