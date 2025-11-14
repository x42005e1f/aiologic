#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from types import TracebackType
from typing import Any, Final, Protocol, TypeVar

from ._semaphore import BinarySemaphore

if sys.version_info >= (3, 11):
    from typing import Self, overload
else:
    from typing_extensions import Self, overload

if sys.version_info >= (3, 9):
    from collections.abc import Callable
else:
    from typing import Callable

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

_LockT = TypeVar("_LockT", bound=(_AALock | _ASLock | _SSLock | _MMLock))

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

    def __init__(self, /, lock: _AALock) -> None: ...
    async def __aenter__(self, /) -> Self: ...
    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...
    def __call__(self, wrapped: _CallableT, /) -> _CallableT: ...

class _ASSynchronizer:
    __slots__ = (
        "_async_acquire",
        "_async_release",
        "_async_synchronized",
    )

    def __init__(self, /, lock: _ASLock) -> None: ...
    async def __aenter__(self, /) -> Self: ...
    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...
    def __call__(self, wrapped: _CallableT, /) -> _CallableT: ...

class _SSSynchronizer:
    __slots__ = (
        "_async_synchronized",
        "_green_acquire",
        "_green_release",
        "_green_synchronized",
    )

    def __init__(self, /, lock: _SSLock) -> None: ...
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

class _MMSynchronizer:
    __slots__ = (
        "_async_acquire",
        "_async_release",
        "_async_synchronized",
        "_green_acquire",
        "_green_release",
        "_green_synchronized",
    )

    def __init__(self, /, lock: _MMLock) -> None: ...
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

_synchronized_meta_lock: Final[BinarySemaphore]

async def _async_synchronized_lock(
    context: _SynchronizedType[_LockT],
    /,
) -> _LockT: ...
def _green_synchronized_lock(
    context: _SynchronizedType[_LockT],
    /,
) -> _LockT: ...
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
