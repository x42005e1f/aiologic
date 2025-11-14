#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import platform
import sys

from functools import partial
from math import inf, isinf, isnan
from typing import TYPE_CHECKING, Final, NoReturn, TypeVar

from aiologic._monkey import import_original
from aiologic.meta import replaces

from ._libraries import current_async_library, current_green_library

if TYPE_CHECKING:
    if sys.version_info >= (3, 9):
        from collections.abc import Awaitable, Callable
    else:
        from typing import Awaitable, Callable

_T = TypeVar("_T")

_DAY_TO_SEC: Final[int] = 24 * 60 * 60

_MS_TO_SEC: Final[int] = -3  # / 1_000
_NS_TO_SEC: Final[int] = -9  # / 1_000_000_000


def _floor_to_float(value: int, pow10: int = 0, /) -> float:
    import decimal

    float_rounds_floor = sys.float_info.rounds in {0, 3}

    # When converting to float, there are two cases:
    # 1. The difference exceeded more than one integer, since the value did not
    #    fit into the significand of the float.
    # 2. The result exceeded the actual maximum, since rounding towards
    #    positive infinity (or to nearest) occurred.
    # Therefore, to represent the maximum most accurately, a special approach
    # to calculation is required. Here is one such approach: we find the
    # nearest representable value in float towards negative infinity that does
    # not exceed one integer in difference, and if there is no such value, just
    # return int.

    max_digits = sys.float_info.dig

    # There are float values with more than max_digits digits, but we ignore
    # them because finding such values would require too much code complexity,
    # which is beyond the scope of this module. After all, we cannot provide
    # perfect sleep accuracy anyway.

    rounding = decimal.ROUND_FLOOR

    @replaces(globals())
    def _floor_to_float(value, pow10=0, /):
        if value < 0:
            msg = "value must be non-negative"
            raise ValueError(msg)

        length = len(str(value))

        if length + pow10 <= max_digits:
            with decimal.localcontext() as ctx:
                ctx.prec = length
                ctx.rounding = rounding

                scaled_value = decimal.Decimal(value).scaleb(pow10)

                if pow10 >= 0:
                    result = float(scaled_value)

                    if result != scaled_value:
                        result = int(scaled_value)

                    return result

                if float_rounds_floor:
                    result = float(scaled_value)

                    if int(result) != scaled_value.to_integral_value():
                        result = int(scaled_value)

                    return result

                ndigits = min(max_digits - length, 0) - pow10

                return float(round(scaled_value, ndigits))

        if pow10 >= 0:
            return value * 10**pow10
        else:
            return value // 10 ** (-pow10)

    return _floor_to_float(value, pow10)


def _threading_seconds_per_sleep() -> float:
    if sys.version_info >= (3, 11):
        # Under the hood, time.sleep() actually works like sleep-until, because
        # starting with Python 3.5, it has to handle interrupts (it is
        # implemented via a loop with delay recomputation). And since Python
        # 3.11, it utilizes functions that internally operate via absolute time
        # (in particular, clock_nanosleep(), to which it passes the deadline
        # directly), which may lead to errors due to overflow. As a result, the
        # current clock reduces the range of acceptable values (and the longer
        # the uptime, the fewer seconds we can use), so to avoid
        # overflow-related errors, we have to choose any fixed window.
        _MAXIMUM_SECONDS_PER_SLEEP = _floor_to_float(2**30 - 1)  # ~35 years
    else:
        if platform.system() != "Windows":
            # select() is only guaranteed to support at least 31 days, and the
            # actual limits implemented are usually not documented, so we have
            # to deal with this. It will also be used on Python >= 3.11, when
            # neither clock_nanosleep() nor nanosleep() are available, but we
            # assume that this is not our case (it is a very specific case, and
            # we cannot effectively detect it).
            _MAXIMUM_SECONDS_PER_SLEEP = _floor_to_float(31 * _DAY_TO_SEC)
        else:
            # due to milliseconds < ULONG_MAX (~50 days)
            # (note that 0xffffffff (=> 4294967.295) is INFINITE)
            _MAXIMUM_SECONDS_PER_SLEEP = _floor_to_float(2**32 - 2, _MS_TO_SEC)

    @replaces(globals())
    def _threading_seconds_per_sleep():
        return _MAXIMUM_SECONDS_PER_SLEEP

    return _threading_seconds_per_sleep()


def _eventlet_seconds_per_sleep() -> float:
    from eventlet.hubs import get_hub

    # see the comment about select() in _threading_seconds_per_sleep()
    _MAXIMUM_SECONDS_PER_SLEEP = _floor_to_float(31 * _DAY_TO_SEC)  # ~31 days

    # due to milliseconds <= INT_MAX (~25 days)
    _MAXIMUM_SECONDS_PER_POLL_SLEEP = _floor_to_float(2**31 - 1, _MS_TO_SEC)

    # handled on the event loop side, so we only avoid int->float errors
    _MAXIMUM_SECONDS_PER_ASYNCIO_SLEEP = sys.float_info.max  # ~6e+300 years

    @replaces(globals())
    def _eventlet_seconds_per_sleep():
        hub_name = get_hub().__module__.rpartition(".")[-1]

        if hub_name == "asyncio":
            return _MAXIMUM_SECONDS_PER_ASYNCIO_SLEEP
        elif hub_name == "epolls" or hub_name == "poll":
            return _MAXIMUM_SECONDS_PER_POLL_SLEEP
        else:
            return _MAXIMUM_SECONDS_PER_SLEEP

    return _eventlet_seconds_per_sleep()


def _gevent_seconds_per_sleep() -> float:
    # due to milliseconds <= UINT64_MAX for CFFI (~6e+11 years)
    _MAXIMUM_SECONDS_PER_SLEEP = _floor_to_float(2**64 - 1, _MS_TO_SEC)

    @replaces(globals())
    def _gevent_seconds_per_sleep():
        return _MAXIMUM_SECONDS_PER_SLEEP

    return _gevent_seconds_per_sleep()


def _asyncio_seconds_per_sleep() -> float:
    # handled on the event loop side, so we only avoid int->float errors
    _MAXIMUM_SECONDS_PER_SLEEP = sys.float_info.max  # ~6e+300 years

    @replaces(globals())
    def _asyncio_seconds_per_sleep():
        return _MAXIMUM_SECONDS_PER_SLEEP

    return _asyncio_seconds_per_sleep()


def _curio_seconds_per_sleep() -> float:
    from curio.meta import _locals

    # see the comment about select() in _threading_seconds_per_sleep()
    _MAXIMUM_SECONDS_PER_SLEEP = _floor_to_float(31 * _DAY_TO_SEC)  # ~31 days

    # due to milliseconds <= INT_MAX (~25 days)
    _MAXIMUM_SECONDS_PER_POLL_SLEEP = _floor_to_float(2**31 - 1, _MS_TO_SEC)

    def _from_runner(name, /):
        attr_name = f"_aiologic_runner_{name}_cell"

        try:
            cell = getattr(_locals, attr_name)
        except AttributeError:
            kernel = getattr(_locals, "kernel", None)

            if kernel is None:
                msg = "no running kernel"
                raise RuntimeError(msg) from None

            cell_index = kernel._runner.__code__.co_freevars.index(name)
            cell = kernel._runner.__closure__[cell_index]

            setattr(_locals, attr_name, cell)
            finalizer = partial(delattr, _locals, attr_name)

            kernel._call_at_shutdown(finalizer)

        return cell.cell_contents

    poll_selectors = {"devpoll", "epoll", "poll"}

    @replaces(globals())
    def _curio_seconds_per_sleep():
        selector = _from_runner("selector_select").__self__
        selector_name = selector.__class__.__name__.rpartition("Selector")[
            0
        ].lower()

        if selector_name in poll_selectors:
            seconds = _MAXIMUM_SECONDS_PER_POLL_SLEEP
        else:
            seconds = _MAXIMUM_SECONDS_PER_SLEEP

        selector_max_timeout = _from_runner("selector_max_timeout")

        if selector_max_timeout and selector_max_timeout <= seconds:
            # handled on the kernel side, so we only avoid int->float errors
            seconds = sys.float_info.max  # ~6e+300 years

        return seconds

    return _curio_seconds_per_sleep()


def _trio_seconds_per_sleep() -> float:
    # handled on the event loop side, so we only avoid int->float errors
    _MAXIMUM_SECONDS_PER_SLEEP = sys.float_info.max  # ~6e+300 years

    @replaces(globals())
    def _trio_seconds_per_sleep():
        return _MAXIMUM_SECONDS_PER_SLEEP

    return _trio_seconds_per_sleep()


def green_seconds_per_sleep() -> float:
    """..."""

    library = current_green_library()

    if library == "threading":
        return _threading_seconds_per_sleep()

    if library == "eventlet":
        return _eventlet_seconds_per_sleep()

    if library == "gevent":
        return _gevent_seconds_per_sleep()

    msg = f"unsupported green library {library!r}"
    raise RuntimeError(msg)


def async_seconds_per_sleep() -> float:
    """..."""

    library = current_async_library()

    if library == "asyncio":
        return _asyncio_seconds_per_sleep()

    if library == "curio":
        return _curio_seconds_per_sleep()

    if library == "trio":
        return _trio_seconds_per_sleep()

    msg = f"unsupported async library {library!r}"
    raise RuntimeError(msg)


def _threading_seconds_per_timeout() -> float:
    # We cannot rely on _thread.TIMEOUT_MAX (threading.TIMEOUT_MAX) because it
    # includes INFINITE until Python 3.11 (see python/cpython#28673).

    if platform.system() != "Windows":
        # due to _PyTime_FromSecondsObject(): SEC_TO_NS (~300.5 years)
        _MAXIMUM_SECONDS_PER_TIMEOUT = _floor_to_float(2**63 - 1, _NS_TO_SEC)
    else:
        # due to milliseconds < ULONG_MAX (~50 days)
        # (note that 0xffffffff (=> 4294967.295) is INFINITE)
        _MAXIMUM_SECONDS_PER_TIMEOUT = _floor_to_float(2**32 - 2, _MS_TO_SEC)

    @replaces(globals())
    def _threading_seconds_per_timeout():
        return _MAXIMUM_SECONDS_PER_TIMEOUT

    return _threading_seconds_per_timeout()


def _eventlet_seconds_per_timeout() -> float:
    global _eventlet_seconds_per_timeout

    result = _eventlet_seconds_per_sleep()

    _eventlet_seconds_per_timeout = _eventlet_seconds_per_sleep

    return result


def _gevent_seconds_per_timeout() -> float:
    global _gevent_seconds_per_timeout

    result = _gevent_seconds_per_sleep()

    _gevent_seconds_per_timeout = _gevent_seconds_per_sleep

    return result


def _asyncio_seconds_per_timeout() -> float:
    global _asyncio_seconds_per_timeout

    result = _asyncio_seconds_per_sleep()

    _asyncio_seconds_per_timeout = _asyncio_seconds_per_sleep

    return result


def _curio_seconds_per_timeout() -> float:
    global _curio_seconds_per_timeout

    result = _curio_seconds_per_sleep()

    _curio_seconds_per_timeout = _curio_seconds_per_sleep

    return result


def _trio_seconds_per_timeout() -> float:
    global _trio_seconds_per_timeout

    result = _trio_seconds_per_sleep()

    _trio_seconds_per_timeout = _trio_seconds_per_sleep

    return result


def green_seconds_per_timeout() -> float:
    """..."""

    library = current_green_library()

    if library == "threading":
        return _threading_seconds_per_timeout()

    if library == "eventlet":
        return _eventlet_seconds_per_timeout()

    if library == "gevent":
        return _gevent_seconds_per_timeout()

    msg = f"unsupported green library {library!r}"
    raise RuntimeError(msg)


def async_seconds_per_timeout() -> float:
    """..."""

    library = current_async_library()

    if library == "asyncio":
        return _asyncio_seconds_per_timeout()

    if library == "curio":
        return _curio_seconds_per_timeout()

    if library == "trio":
        return _trio_seconds_per_timeout()

    msg = f"unsupported async library {library!r}"
    raise RuntimeError(msg)


def _threading_clock() -> float:
    global _threading_clock

    if sys.version_info >= (3, 13) or platform.system() != "Windows":
        _threading_clock = import_original("time", "monotonic")
    else:  # see python/cpython#88494
        _threading_clock = import_original("time", "perf_counter")

    return _threading_clock()


def _eventlet_clock() -> float:
    from eventlet.hubs import get_hub

    @replaces(globals())
    def _eventlet_clock():
        return get_hub().clock()

    return _eventlet_clock()


def _gevent_clock() -> float:
    from gevent import get_hub

    @replaces(globals())
    def _gevent_clock():
        loop = get_hub().loop

        loop.update_now()

        return loop.now()

    return _gevent_clock()


def _asyncio_clock() -> float:
    from asyncio import get_running_loop

    @replaces(globals())
    def _asyncio_clock():
        return get_running_loop().time()

    return _asyncio_clock()


def _curio_clock() -> float:
    from functools import partial

    from curio.meta import _locals

    @replaces(globals())
    def _curio_clock():
        try:
            cell = _locals._aiologic_clock_cell
        except AttributeError:
            kernel = getattr(_locals, "kernel", None)

            if kernel is None:
                msg = "no running kernel"
                raise RuntimeError(msg) from None

            trap = kernel._traps["trap_clock"]

            cell_index = trap.__code__.co_freevars.index("time_monotonic")
            cell = trap.__closure__[cell_index]

            _locals._aiologic_clock_cell = cell
            finalizer = partial(delattr, _locals, "_aiologic_clock_cell")

            kernel._call_at_shutdown(finalizer)

        return cell.cell_contents()

    return _curio_clock()


def _trio_clock() -> float:
    global _trio_clock

    from trio import current_time as _trio_clock

    return _trio_clock()


def green_clock() -> float:
    """..."""

    library = current_green_library()

    if library == "threading":
        return _threading_clock()

    if library == "eventlet":
        return _eventlet_clock()

    if library == "gevent":
        return _gevent_clock()

    msg = f"unsupported green library {library!r}"
    raise RuntimeError(msg)


def async_clock() -> float:
    """..."""

    library = current_async_library()

    if library == "asyncio":
        return _asyncio_clock()

    if library == "curio":
        return _curio_clock()

    if library == "trio":
        return _trio_clock()

    msg = f"unsupported async library {library!r}"
    raise RuntimeError(msg)


def _threading_sleep(seconds: float, /) -> None:
    global _threading_sleep

    _threading_sleep = import_original("time", "sleep")

    _threading_sleep(seconds)


def _eventlet_sleep(seconds: float, /) -> None:
    global _eventlet_sleep

    from eventlet import sleep as _eventlet_sleep

    _eventlet_sleep(seconds)


def _gevent_sleep(seconds: float, /) -> None:
    global _gevent_sleep

    from gevent import sleep as _gevent_sleep

    _gevent_sleep(seconds)


async def _asyncio_sleep(seconds: float, /) -> None:
    global _asyncio_sleep

    from asyncio import sleep as _asyncio_sleep

    await _asyncio_sleep(seconds)


async def _curio_sleep(seconds: float, /) -> None:
    global _curio_sleep

    from curio import sleep as _curio_sleep

    await _curio_sleep(seconds)


async def _trio_sleep(seconds: float, /) -> None:
    global _trio_sleep

    from trio import sleep as _trio_sleep

    await _trio_sleep(seconds)


def _green_long_sleep(
    sleep: Callable[[float], _T],
    seconds: float,
    /,
    seconds_per_sleep: float,
    *,
    clock: Callable[[], float],
    check: bool = False,
) -> _T:
    if seconds > seconds_per_sleep:
        deadline = clock() + seconds

        while True:
            result = sleep(seconds_per_sleep)

            if check and result:
                return result

            seconds = deadline - clock()

            if seconds <= 0:
                return result

            if seconds <= seconds_per_sleep:
                break

    return sleep(seconds)


async def _async_long_sleep(
    sleep: Callable[[float], Awaitable[_T]],
    seconds: float,
    /,
    seconds_per_sleep: float,
    *,
    clock: Callable[[], float],
    check: bool = False,
) -> _T:
    if seconds > seconds_per_sleep:
        deadline = clock() + seconds

        while True:
            result = await sleep(seconds_per_sleep)

            if check and result:
                return result

            seconds = deadline - clock()

            if seconds <= 0:
                return result

            if seconds <= seconds_per_sleep:
                break

    return await sleep(seconds)


def green_sleep(seconds: float, /) -> None:
    """..."""

    if isinstance(seconds, int):
        try:
            seconds = float(seconds)
        except OverflowError:
            seconds = (-1 if seconds < 0 else 1) * inf

    if isnan(seconds):
        msg = "seconds must be non-NaN"
        raise ValueError(msg)

    if seconds < 0:
        msg = "seconds must be non-negative"
        raise ValueError(msg)

    if isinf(seconds):
        green_sleep_forever()

    library = current_green_library()

    if library == "threading":
        clock = _threading_clock
        sleep = _threading_sleep
        seconds_per_sleep = _threading_seconds_per_sleep()
    elif library == "eventlet":
        clock = _eventlet_clock
        sleep = _eventlet_sleep
        seconds_per_sleep = _eventlet_seconds_per_sleep()
    elif library == "gevent":
        clock = _gevent_clock
        sleep = _gevent_sleep
        seconds_per_sleep = _gevent_seconds_per_sleep()
    else:
        msg = f"unsupported green library {library!r}"
        raise RuntimeError(msg)

    _green_long_sleep(sleep, seconds, seconds_per_sleep, clock=clock)


async def async_sleep(seconds: float, /) -> None:
    """..."""

    if isinstance(seconds, int):
        try:
            seconds = float(seconds)
        except OverflowError:
            seconds = (-1 if seconds < 0 else 1) * inf

    if isnan(seconds):
        msg = "seconds must not be NaN"
        raise ValueError(msg)

    if seconds < 0:
        msg = "seconds must be non-negative"
        raise ValueError(msg)

    if isinf(seconds):
        await async_sleep_forever()

    library = current_async_library()

    if library == "asyncio":
        clock = _asyncio_clock
        sleep = _asyncio_sleep
        seconds_per_sleep = _asyncio_seconds_per_sleep()
    elif library == "curio":
        clock = _curio_clock
        sleep = _curio_sleep
        seconds_per_sleep = _curio_seconds_per_sleep()
    elif library == "trio":
        clock = _trio_clock
        sleep = _trio_sleep
        seconds_per_sleep = _trio_seconds_per_sleep()
    else:
        msg = f"unsupported async library {library!r}"
        raise RuntimeError(msg)

    await _async_long_sleep(sleep, seconds, seconds_per_sleep, clock=clock)


def _threading_sleep_until(deadline: float, /) -> None:
    _threading_sleep(max(0, deadline - _threading_clock()))


def _eventlet_sleep_until(deadline: float, /) -> None:
    _eventlet_sleep(max(0, deadline - _eventlet_clock()))


def _gevent_sleep_until(deadline: float, /) -> None:
    from gevent import get_hub

    @replaces(globals())
    def _gevent_sleep_until(deadline):
        hub = get_hub()
        loop = hub.loop

        seconds = deadline - loop.now()

        if seconds <= 0:
            _gevent_sleep(0)
        else:
            with loop.timer(seconds) as timer:
                hub.wait(timer)

    _gevent_sleep_until(deadline)


async def _asyncio_sleep_until(deadline: float, /) -> None:
    from asyncio import get_running_loop

    def _notify(future):
        if future.cancelled():
            return

        future.set_result(None)

    @replaces(globals())
    async def _asyncio_sleep_until(deadline):
        loop = get_running_loop()

        if deadline - loop.time() <= 0:
            await _asyncio_sleep(0)
        else:
            future = loop.create_future()
            handle = loop.call_at(deadline, _notify, future)

            try:
                await future
            finally:
                handle.cancel()

    await _asyncio_sleep_until(deadline)


async def _curio_sleep_until(deadline: float, /) -> None:
    await _curio_sleep(max(0, deadline - _curio_clock()))


async def _trio_sleep_until(deadline: float, /) -> None:
    global _trio_sleep_until

    from trio import sleep_until as _trio_sleep_until

    await _trio_sleep_until(deadline)


def _green_long_sleep_until(
    sleep_until: Callable[[float], _T],
    deadline: float,
    /,
    seconds_per_sleep: float,
    *,
    clock: Callable[[], float],
    check: bool = False,
) -> _T:
    seconds = deadline - (timestamp := clock())

    while seconds > seconds_per_sleep:
        result = sleep_until(timestamp + seconds_per_sleep)

        if check and result:
            return result

        seconds = deadline - (timestamp := clock())

        if seconds <= 0:
            return result

    return sleep_until(deadline)


async def _async_long_sleep_until(
    sleep_until: Callable[[float], Awaitable[_T]],
    deadline: float,
    /,
    seconds_per_sleep: float,
    *,
    clock: Callable[[], float],
    check: bool = False,
) -> _T:
    seconds = deadline - (timestamp := clock())

    while seconds > seconds_per_sleep:
        result = await sleep_until(timestamp + seconds_per_sleep)

        if check and result:
            return result

        seconds = deadline - (timestamp := clock())

        if seconds <= 0:
            return result

    return await sleep_until(deadline)


def green_sleep_until(deadline: float, /) -> None:
    """..."""

    if isinstance(deadline, int):
        try:
            deadline = float(deadline)
        except OverflowError:
            deadline = (-1 if deadline < 0 else 1) * inf

    if isnan(deadline):
        msg = "deadline must be non-NaN"
        raise ValueError(msg)

    if isinf(deadline) and deadline > 0:
        green_sleep_forever()

    library = current_green_library()

    if library == "threading":
        clock = _threading_clock
        sleep_until = _threading_sleep_until
        seconds_per_sleep = _threading_seconds_per_sleep()
    elif library == "eventlet":
        clock = _eventlet_clock
        sleep_until = _eventlet_sleep_until
        seconds_per_sleep = _eventlet_seconds_per_sleep()
    elif library == "gevent":
        clock = _gevent_clock
        sleep_until = _gevent_sleep_until
        seconds_per_sleep = _gevent_seconds_per_sleep()
    else:
        msg = f"unsupported green library {library!r}"
        raise RuntimeError(msg)

    _green_long_sleep_until(
        sleep_until,
        deadline,
        seconds_per_sleep,
        clock=clock,
    )


async def async_sleep_until(deadline: float, /) -> None:
    """..."""

    if isinstance(deadline, int):
        try:
            deadline = float(deadline)
        except OverflowError:
            deadline = (-1 if deadline < 0 else 1) * inf

    if isnan(deadline):
        msg = "deadline must be non-NaN"
        raise ValueError(msg)

    if isinf(deadline) and deadline > 0:
        await async_sleep_forever()

    library = current_async_library()

    if library == "asyncio":
        clock = _asyncio_clock
        sleep_until = _asyncio_sleep_until
        seconds_per_sleep = _asyncio_seconds_per_sleep()
    elif library == "curio":
        clock = _curio_clock
        sleep_until = _curio_sleep_until
        seconds_per_sleep = _curio_seconds_per_sleep()
    elif library == "trio":
        clock = _trio_clock
        sleep_until = _trio_sleep_until
        seconds_per_sleep = _trio_seconds_per_sleep()
    else:
        msg = f"unsupported async library {library!r}"
        raise RuntimeError(msg)

    await _async_long_sleep_until(
        sleep_until,
        deadline,
        seconds_per_sleep,
        clock=clock,
    )


def _threading_sleep_forever() -> NoReturn:
    if sys.version_info >= (3, 14) or platform.system() != "Windows":
        from ._locks import create_thread_lock

        @replaces(globals())
        def _threading_sleep_forever():
            lock = create_thread_lock()
            lock.acquire()
            lock.acquire()

    else:  # see python/cpython#74157 or python/cpython#125541

        @replaces(globals())
        def _threading_sleep_forever():
            while True:
                _threading_sleep(_threading_seconds_per_sleep())

    _threading_sleep_forever()


def _eventlet_sleep_forever() -> NoReturn:
    from eventlet.hubs import get_hub

    @replaces(globals())
    def _eventlet_sleep_forever():
        get_hub().switch()

    _eventlet_sleep_forever()


def _gevent_sleep_forever() -> NoReturn:
    from gevent import get_hub

    @replaces(globals())
    def _gevent_sleep_forever():
        get_hub().switch()

    _gevent_sleep_forever()


async def _asyncio_sleep_forever() -> NoReturn:
    from asyncio import get_running_loop

    @replaces(globals())
    async def _asyncio_sleep_forever():
        await get_running_loop().create_future()

    await _asyncio_sleep_forever()


async def _curio_sleep_forever() -> NoReturn:
    from . import _waiters

    @replaces(globals())
    async def _curio_sleep_forever():
        await _waiters._create_curio_waiter()

    await _curio_sleep_forever()


async def _trio_sleep_forever() -> NoReturn:
    from trio.lowlevel import Abort, wait_task_rescheduled

    def _abort(raise_cancel):
        return Abort.SUCCEEDED

    @replaces(globals())
    async def _trio_sleep_forever():
        await wait_task_rescheduled(_abort)

    await _trio_sleep_forever()


def green_sleep_forever() -> NoReturn:
    """..."""

    library = current_green_library()

    if library == "threading":
        _threading_sleep_forever()
    elif library == "eventlet":
        _eventlet_sleep_forever()
    elif library == "gevent":
        _gevent_sleep_forever()
    else:
        msg = f"unsupported green library {library!r}"
        raise RuntimeError(msg)

    msg = "should never have been rescheduled"
    raise RuntimeError(msg)


async def async_sleep_forever() -> NoReturn:
    """..."""

    library = current_async_library()

    if library == "asyncio":
        await _asyncio_sleep_forever()
    elif library == "curio":
        await _curio_sleep_forever()
    elif library == "trio":
        await _trio_sleep_forever()
    else:
        msg = f"unsupported async library {library!r}"
        raise RuntimeError(msg)

    msg = "should never have been rescheduled"
    raise RuntimeError(msg)
