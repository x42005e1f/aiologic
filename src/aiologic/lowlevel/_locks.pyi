#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from types import TracebackType
from typing import Final, Literal, NoReturn, TypeVar, final

from aiologic.meta import MISSING, MissingType

if sys.version_info >= (3, 11):
    from typing import overload
else:
    from typing_extensions import overload

if sys.version_info >= (3, 9):
    from collections.abc import Callable
else:
    from typing import Callable

_T = TypeVar("_T")

@final
class ThreadLock:
    def __enter__(self, /) -> bool: ...
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
        /,
    ) -> None: ...
    if sys.version_info >= (3, 9):
        def _at_fork_reinit(self, /) -> None: ...
    def acquire(
        self,
        /,
        blocking: bool = True,
        timeout: float = -1,
    ) -> bool: ...
    def release(self, /) -> None: ...
    def locked(self, /) -> bool: ...

    # Obsolete synonyms

    def acquire_lock(
        self,
        /,
        blocking: bool = True,
        timeout: float = -1,
    ) -> bool: ...
    def release_lock(self, /) -> None: ...
    def locked_lock(self, /) -> bool: ...

@final
class ThreadRLock:
    def __enter__(self, /) -> bool: ...
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
        /,
    ) -> None: ...
    if sys.version_info >= (3, 9):
        def _at_fork_reinit(self, /) -> None: ...
    def acquire(
        self,
        /,
        blocking: bool = True,
        timeout: float = -1,
    ) -> bool: ...
    def release(self, /) -> None: ...
    if sys.version_info >= (3, 14):
        def locked(self, /) -> bool: ...

    # Internal methods used by condition variables

    def _acquire_restore(self, /, state: tuple[int, int]) -> None: ...
    def _release_save(self, /) -> tuple[int, int]: ...
    def _is_owned(self, /) -> bool: ...

    # Internal method used for reentrancy checks

    if sys.version_info >= (3, 11):
        def _recursion_count(self, /) -> int: ...

@final
class ThreadOnceLock:
    def __enter__(self, /) -> bool: ...
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
        /,
    ) -> None: ...
    if sys.version_info >= (3, 9):
        def _at_fork_reinit(self, /) -> None: ...
    def acquire(
        self,
        /,
        blocking: bool = True,
        timeout: float = -1,
    ) -> bool: ...
    def release(self, /) -> None: ...
    if sys.version_info >= (3, 14):
        def locked(self, /) -> bool: ...

    # Internal methods used by condition variables

    def _acquire_restore(self, /, state: tuple[int, int]) -> None: ...
    def _release_save(self, /) -> tuple[int, int]: ...
    def _is_owned(self, /) -> bool: ...

    # Internal method used for reentrancy checks

    if sys.version_info >= (3, 11):
        def _recursion_count(self, /) -> int: ...

def _get_count(self: ThreadOnceLock, /) -> int: ...
def _get_owner(self: ThreadOnceLock, /) -> int | None: ...

@final
class ThreadDummyLock:
    def __new__(cls, /) -> ThreadDummyLock: ...
    def __copy__(self, /) -> ThreadDummyLock: ...
    def __enter__(self, /) -> Literal[True]: ...
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
        /,
    ) -> None: ...
    if sys.version_info >= (3, 9):
        def _at_fork_reinit(self, /) -> None: ...
    def acquire(
        self,
        /,
        blocking: bool = True,
        timeout: float = -1,
    ) -> Literal[True]: ...
    def release(self, /) -> None: ...
    def locked(self, /) -> Literal[False]: ...

    # Internal methods used by condition variables

    def _acquire_restore(self, /, state: tuple[int, int]) -> None: ...
    def _release_save(self, /) -> NoReturn: ...
    def _is_owned(self, /) -> Literal[False]: ...

    # Internal method used for reentrancy checks

    if sys.version_info >= (3, 11):
        def _recursion_count(self, /) -> Literal[0]: ...

THREAD_DUMMY_LOCK: Final[ThreadDummyLock]

def create_thread_lock() -> ThreadLock: ...
def create_thread_rlock() -> ThreadRLock: ...
def create_thread_oncelock() -> ThreadOnceLock: ...
@overload
def once(
    wrapped: MissingType = MISSING,
    /,
    *,
    reentrant: bool = False,
) -> Callable[[Callable[[], _T]], Callable[[], _T]]: ...
@overload
def once(wrapped: Callable[[], _T], /) -> Callable[[], _T]: ...
