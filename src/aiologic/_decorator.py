#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from inspect import iscoroutinefunction
from typing import TYPE_CHECKING, Any, Final, Protocol, TypeVar, Union

from wrapt import FunctionWrapper, decorator

from ._lock import RLock
from ._semaphore import BinarySemaphore

if sys.version_info >= (3, 11):
    from typing import overload
else:
    from typing_extensions import overload

if sys.version_info >= (3, 9):
    from collections.abc import Callable
else:
    from typing import Callable

if TYPE_CHECKING:
    from types import TracebackType

    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self

_CallableT = TypeVar("_CallableT", bound=Callable[..., Any])


class _AALock(Protocol):
    __slots__ = ()

    async def __aenter__(self, /) -> object: ...
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
        /,
    ) -> object: ...
    async def acquire(self, /) -> object: ...
    async def release(self, /) -> object: ...


class _ASLock(Protocol):
    __slots__ = ()

    async def __aenter__(self, /) -> object: ...
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
        /,
    ) -> object: ...
    async def acquire(self, /) -> object: ...
    def release(self, /) -> object: ...


class _SSLock(Protocol):
    __slots__ = ()

    def __enter__(self, /) -> object: ...
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
        /,
    ) -> object: ...
    def acquire(self, /) -> object: ...
    def release(self, /) -> object: ...


class _MMLock(Protocol):
    __slots__ = ()

    async def __aenter__(self, /) -> object: ...
    def __enter__(self, /) -> object: ...
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
        /,
    ) -> object: ...
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
        /,
    ) -> object: ...
    async def async_acquire(self, /) -> object: ...
    def async_release(self, /) -> object: ...
    def green_acquire(self, /) -> object: ...
    def green_release(self, /) -> object: ...


_LockT = TypeVar("_LockT", bound=Union[_AALock, _ASLock, _SSLock, _MMLock])


class _SynchronizedType(Protocol[_LockT]):
    __slots__ = ()

    _synchronized_lock: _LockT


class _SynchronizedDecorator(Protocol):
    __slots__ = ()

    async def __aenter__(self, /) -> Self: ...
    def __enter__(self, /) -> Self: ...
    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...
    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...
    def __call__(self, wrapped: _CallableT, /) -> _CallableT: ...


class _AASynchronizer:
    __slots__ = (
        "_async_acquire",
        "_async_release",
        "_async_synchronized",
    )

    def __init__(self, /, lock: _AALock) -> None:
        self._async_acquire = async_acquire = lock.acquire
        self._async_release = async_release = lock.release

        @decorator
        async def _async_synchronized(wrapped, instance, args, kwargs, /):
            await async_acquire()

            try:
                return await wrapped(*args, **kwargs)
            finally:
                await async_release()

        self._async_synchronized = _async_synchronized

    async def __aenter__(self, /) -> Self:
        await self._async_acquire()

        return self

    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self._async_release()

    def __call__(self, wrapped: _CallableT, /) -> _CallableT:
        if not iscoroutinefunction(wrapped):
            msg = f"a coroutine function was expected, got {wrapped!r}"
            raise TypeError(msg)

        return self._async_synchronized(wrapped)


class _ASSynchronizer:
    __slots__ = (
        "_async_acquire",
        "_async_release",
        "_async_synchronized",
    )

    def __init__(self, /, lock: _ASLock) -> None:
        self._async_acquire = async_acquire = lock.acquire
        self._async_release = async_release = lock.release

        @decorator
        async def _async_synchronized(wrapped, instance, args, kwargs, /):
            await async_acquire()

            try:
                return await wrapped(*args, **kwargs)
            finally:
                async_release()

        self._async_synchronized = _async_synchronized

    async def __aenter__(self, /) -> Self:
        await self._async_acquire()

        return self

    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._async_release()

    def __call__(self, wrapped: _CallableT, /) -> _CallableT:
        if not iscoroutinefunction(wrapped):
            msg = f"a coroutine function was expected, got {wrapped!r}"
            raise TypeError(msg)

        return self._async_synchronized(wrapped)


class _SSSynchronizer:
    __slots__ = (
        "_async_synchronized",
        "_green_acquire",
        "_green_release",
        "_green_synchronized",
    )

    def __init__(self, /, lock: _SSLock) -> None:
        self._green_acquire = green_acquire = lock.acquire
        self._green_release = green_release = lock.release

        @decorator
        async def _async_synchronized(wrapped, instance, args, kwargs, /):
            green_acquire()

            try:
                return await wrapped(*args, **kwargs)
            finally:
                green_release()

        @decorator
        def _green_synchronized(wrapped, instance, args, kwargs, /):
            green_acquire()

            try:
                return wrapped(*args, **kwargs)
            finally:
                green_release()

        self._async_synchronized = _async_synchronized
        self._green_synchronized = _green_synchronized

    async def __aenter__(self, /) -> Self:
        self._green_acquire()

        return self

    def __enter__(self, /) -> Self:
        self._green_acquire()

        return self

    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._green_release()

    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._green_release()

    def __call__(self, wrapped: _CallableT, /) -> _CallableT:
        if iscoroutinefunction(wrapped):
            return self._async_synchronized(wrapped)
        else:
            return self._green_synchronized(wrapped)


class _MMSynchronizer:
    __slots__ = (
        "_async_acquire",
        "_async_release",
        "_async_synchronized",
        "_green_acquire",
        "_green_release",
        "_green_synchronized",
    )

    def __init__(self, /, lock: _MMLock) -> None:
        self._async_acquire = async_acquire = lock.async_acquire
        self._async_release = async_release = lock.async_release

        self._green_acquire = green_acquire = lock.green_acquire
        self._green_release = green_release = lock.green_release

        @decorator
        async def _async_synchronized(wrapped, instance, args, kwargs, /):
            await async_acquire()

            try:
                return await wrapped(*args, **kwargs)
            finally:
                async_release()

        @decorator
        def _green_synchronized(wrapped, instance, args, kwargs, /):
            green_acquire()

            try:
                return wrapped(*args, **kwargs)
            finally:
                green_release()

        self._async_synchronized = _async_synchronized
        self._green_synchronized = _green_synchronized

    async def __aenter__(self, /) -> Self:
        await self._async_acquire()

        return self

    def __enter__(self, /) -> Self:
        self._green_acquire()

        return self

    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._async_release()

    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._green_release()

    def __call__(self, wrapped: _CallableT, /) -> _CallableT:
        if iscoroutinefunction(wrapped):
            return self._async_synchronized(wrapped)
        else:
            return self._green_synchronized(wrapped)


_synchronized_meta_lock: Final[BinarySemaphore] = BinarySemaphore()


async def _async_synchronized_lock(
    context: _SynchronizedType[_LockT],
    /,
) -> _LockT:
    try:
        return context._synchronized_lock
    except AttributeError:
        pass

    async with _synchronized_meta_lock:
        try:
            return context._synchronized_lock
        except AttributeError:
            pass

        context._synchronized_lock = RLock()

    return context._synchronized_lock


def _green_synchronized_lock(context: _SynchronizedType[_LockT], /) -> _LockT:
    try:
        return context._synchronized_lock
    except AttributeError:
        pass

    with _synchronized_meta_lock:
        try:
            return context._synchronized_lock
        except AttributeError:
            pass

        context._synchronized_lock = RLock()

    return context._synchronized_lock


class __SynchronizedDecoratorImpl(FunctionWrapper):
    __slots__ = ("__lock",)

    async def __aenter__(self, /):
        self.__lock = await _async_synchronized_lock(self.__wrapped__)

        if hasattr(self.__lock, "__aenter__"):
            await self.__lock.__aenter__()
        else:
            self.__lock.__enter__()

        return self

    def __enter__(self, /):
        self.__lock = _green_synchronized_lock(self.__wrapped__)

        self.__lock.__enter__()

        return self

    async def __aexit__(self, /, exc_type, exc_value, traceback):
        if hasattr(self.__lock, "__aexit__"):
            await self.__lock.__aexit__(exc_type, exc_value, traceback)
        else:
            self.__lock.__exit__(exc_type, exc_value, traceback)

    def __exit__(self, /, exc_type, exc_value, traceback):
        self.__lock.__exit__(exc_type, exc_value, traceback)


async def __async_synchronized_wrapper(wrapped, instance, args, kwargs, /):
    if instance is not None:
        context = instance
    else:
        context = wrapped

    lock = await _async_synchronized_lock(context)

    if hasattr(lock, "__aenter__") and hasattr(lock, "__aexit__"):
        async with lock:
            return await wrapped(*args, **kwargs)
    else:
        with lock:
            return await wrapped(*args, **kwargs)


def __green_synchronized_wrapper(wrapped, instance, args, kwargs, /):
    if instance is not None:
        context = instance
    else:
        context = wrapped

    with _green_synchronized_lock(context):
        return wrapped(*args, **kwargs)


@overload
def synchronized(  # type: ignore[overload-overlap]
    wrapped: _AALock,
    /,
) -> _AASynchronizer: ...
@overload
def synchronized(  # type: ignore[overload-overlap]
    wrapped: _ASLock,
    /,
) -> _ASSynchronizer: ...
@overload
def synchronized(wrapped: _SSLock, /) -> _SSSynchronizer: ...
@overload
def synchronized(wrapped: _MMLock, /) -> _MMSynchronizer: ...
@overload
def synchronized(
    wrapped: _SynchronizedType[_LockT],
    /,
) -> _SynchronizedDecorator: ...
@overload
def synchronized(  # type: ignore[overload-overlap]
    wrapped: _CallableT,
    /,
) -> _CallableT: ...
@overload
def synchronized(wrapped: object, /) -> _SynchronizedDecorator: ...
def synchronized(wrapped, /):
    """..."""

    if hasattr(wrapped, "acquire") and hasattr(wrapped, "release"):
        if iscoroutinefunction(wrapped.acquire):
            if iscoroutinefunction(wrapped.release):
                return _AASynchronizer(wrapped)

            return _ASSynchronizer(wrapped)

        return _SSSynchronizer(wrapped)

    if all(
        hasattr(wrapped, name)
        for name in [
            "async_acquire",
            "async_release",
            "green_acquire",
            "green_release",
        ]
    ):
        return _MMSynchronizer(wrapped)

    if iscoroutinefunction(wrapped):
        return __SynchronizedDecoratorImpl(
            wrapped=wrapped,
            wrapper=__async_synchronized_wrapper,
        )

    return __SynchronizedDecoratorImpl(
        wrapped=wrapped,
        wrapper=__green_synchronized_wrapper,
    )
