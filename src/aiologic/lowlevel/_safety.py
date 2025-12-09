#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from contextvars import ContextVar, Token
from inspect import isawaitable, iscoroutinefunction
from typing import TYPE_CHECKING, Any, Literal, TypeVar

from wrapt import ObjectProxy, decorator

from aiologic.meta import MISSING, MissingType, replaces

from ._threads import current_thread_ident

if sys.version_info >= (3, 11):
    from typing import overload
else:
    from typing_extensions import overload

if sys.version_info >= (3, 9):
    from collections.abc import Awaitable, Callable
else:
    from typing import Awaitable, Callable

if TYPE_CHECKING:
    from types import TracebackType

_AwaitableT = TypeVar("_AwaitableT", bound=Awaitable[Any])
_CallableT = TypeVar("_CallableT", bound=Callable[..., Any])

_signal_safety_used: bool = False
_signal_safety_cvar: ContextVar[tuple[int, bool | None]] = ContextVar(
    "_signal_safety_cvar",
    default=(
        current_thread_ident(),
        None,
    ),
)


def _signal_safety_reset(token: Token[tuple[int, bool | None]], /) -> None:
    pass


def _signal_safety_set(enabled: bool) -> Token[tuple[int, bool | None]]:
    global _signal_safety_used

    _signal_safety_used = True

    @replaces(globals())
    def _signal_safety_reset(
        token: Token[tuple[int, bool | None]],
        /,
    ) -> None:
        _signal_safety_cvar.reset(token)

    @replaces(globals())
    def _signal_safety_set(enabled):
        return _signal_safety_cvar.set((
            current_thread_ident(),
            enabled,
        ))

    return _signal_safety_set(enabled)


def signal_safety_enabled() -> bool:
    """
    Return :data:`True` if signal-safety is enabled in the current context,
    :data:`False` otherwise.
    """

    if _signal_safety_used:
        ident, maybe_enabled = _signal_safety_cvar.get()

        if maybe_enabled is not None and ident == current_thread_ident():
            return maybe_enabled

    return False


class _SignalSafetyManager:
    __slots__ = ("__token",)

    async def __aenter__(self, /) -> Literal[True]:
        self.__token = _signal_safety_set(True)

        return True

    def __enter__(self, /) -> Literal[True]:
        self.__token = _signal_safety_set(True)

        return True

    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        _signal_safety_reset(self.__token)

    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        _signal_safety_reset(self.__token)


class _NoSignalSafetyManager:
    __slots__ = ("__token",)

    async def __aenter__(self, /) -> Literal[False]:
        self.__token = _signal_safety_set(False)

        return False

    def __enter__(self, /) -> Literal[False]:
        self.__token = _signal_safety_set(False)

        return False

    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        _signal_safety_reset(self.__token)

    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        _signal_safety_reset(self.__token)


class __AwaitableWithSignalSafety(ObjectProxy):
    __slots__ = ()

    def __await__(self, /):
        token = _signal_safety_set(True)

        try:
            return (yield from self.__wrapped__.__await__())
        except BaseException:
            self = None  # noqa: PLW0642
            raise
        finally:
            _signal_safety_reset(token)


class __AwaitableWithNoSignalSafety(ObjectProxy):
    __slots__ = ()

    def __await__(self, /):
        token = _signal_safety_set(False)

        try:
            return (yield from self.__wrapped__.__await__())
        except BaseException:
            self = None  # noqa: PLW0642
            raise
        finally:
            _signal_safety_reset(token)


@decorator
async def __enable_async_signal_safety(wrapped, instance, args, kwargs, /):
    token = _signal_safety_set(True)

    try:
        return await wrapped(*args, **kwargs)
    finally:
        _signal_safety_reset(token)


@decorator
async def __disable_async_signal_safety(wrapped, instance, args, kwargs, /):
    token = _signal_safety_set(False)

    try:
        return await wrapped(*args, **kwargs)
    finally:
        _signal_safety_reset(token)


@decorator
def __enable_green_signal_safety(wrapped, instance, args, kwargs, /):
    token = _signal_safety_set(True)

    try:
        return wrapped(*args, **kwargs)
    finally:
        _signal_safety_reset(token)


@decorator
def __disable_green_signal_safety(wrapped, instance, args, kwargs, /):
    token = _signal_safety_set(False)

    try:
        return wrapped(*args, **kwargs)
    finally:
        _signal_safety_reset(token)


@overload
def enable_signal_safety(
    wrapped: MissingType = MISSING,
    /,
) -> _SignalSafetyManager: ...
@overload
def enable_signal_safety(wrapped: _AwaitableT, /) -> _AwaitableT: ...
@overload
def enable_signal_safety(wrapped: _CallableT, /) -> _CallableT: ...
def enable_signal_safety(wrapped=MISSING, /):
    """
    Enable signal-safety in the current context.

    If a callable object is passed, it is wrapped with a universal decorator
    and a callable proxy is returned. If an awaitable object is passed, it is
    also wrapped and an awaitable proxy is returned. If nothing is passed, a
    sync/async context manager is returned.

    To distinguish between green and async functions,
    :func:`inspect.iscoroutinefunction` is used. Therefore, if you implement
    your own callable object that returns a coroutine object, consider using
    :func:`inspect.markcoroutinefunction`.

    Example:
      >>> signal_safety_enabled()
      False
      >>> async with enable_signal_safety():
      ...     signal_safety_enabled()
      True
      >>> signal_safety_enabled()
      False
      >>> async def test():
      ...     return signal_safety_enabled()
      >>> await test()
      False
      >>> await enable_signal_safety(test)()  # for a callable object
      True
      >>> await enable_signal_safety(test())  # for an awaitable object
      True
      >>> await test()
      False
    """

    if wrapped is MISSING:
        return _SignalSafetyManager()

    if isawaitable(wrapped):
        return __AwaitableWithSignalSafety(wrapped)

    if iscoroutinefunction(wrapped):
        return __enable_async_signal_safety(wrapped)

    return __enable_green_signal_safety(wrapped)


@overload
def disable_signal_safety(
    wrapped: MissingType = MISSING,
    /,
) -> _NoSignalSafetyManager: ...
@overload
def disable_signal_safety(wrapped: _AwaitableT, /) -> _AwaitableT: ...
@overload
def disable_signal_safety(wrapped: _CallableT, /) -> _CallableT: ...
def disable_signal_safety(wrapped=MISSING, /):
    """
    Disable signal-safety in the current context.

    Like :func:`enable_signal_safety`, but with the opposite effect.

    Example:
      >>> with enable_signal_safety():
      ...     signal_safety_enabled()
      ...     with disable_signal_safety():
      ...         signal_safety_enabled()
      ...     signal_safety_enabled()
      True
      False
      True
    """

    if wrapped is MISSING:
        return _NoSignalSafetyManager()

    if isawaitable(wrapped):
        return __AwaitableWithNoSignalSafety(wrapped)

    if iscoroutinefunction(wrapped):
        return __disable_async_signal_safety(wrapped)

    return __disable_green_signal_safety(wrapped)
