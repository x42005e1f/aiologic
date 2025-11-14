#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from functools import partial, wraps
from typing import TYPE_CHECKING, Any, Final, Literal, NoReturn, TypeVar, final

from aiologic._monkey import import_original
from aiologic.meta import MISSING, MissingType

from . import _checkpoints
from ._threads import current_thread_ident

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

_T = TypeVar("_T")

# third-party patchers can break the original objects from the threading
# module, so we need to use the _thread module in the first place

ThreadLock = import_original("_thread", "LockType")

try:
    ThreadRLock = import_original("_thread", "RLock")
except ImportError:

    @final
    class ThreadRLock:
        __slots__ = (
            "__weakref__",
            "_block",
            "_count",
            "_owner",
        )

        _block: ThreadLock  # not provided by _thread.RLock
        _count: int  # not provided by _thread.RLock
        _owner: int | None  # not provided by _thread.RLock

        def __init__(self, /) -> None:
            self._block = create_thread_lock()
            self._count = 0
            self._owner = None

        def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn:
            bcs = ThreadRLock
            bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

            msg = f"type '{bcs_repr}' is not an acceptable base type"
            raise TypeError(msg)

        def __reduce__(self, /) -> NoReturn:
            msg = f"cannot reduce {self!r}"
            raise TypeError(msg)

        def __repr__(self, /) -> str:
            cls = self.__class__
            cls_repr = f"{cls.__module__}.{cls.__qualname__}"

            if self._block.locked():
                status = "locked"
            else:
                status = "unlocked"

            object_repr = f"{status} {cls_repr} object"
            extra = f"owner={self._owner!r} count={self._count!r}"

            return f"<{object_repr} {extra} at {id(self):#x}>"

        def __enter__(self, /) -> bool:
            return self.acquire()

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc_value: BaseException | None,
            traceback: TracebackType | None,
            /,
        ) -> None:
            self.release()

        if sys.version_info >= (3, 9):

            def _at_fork_reinit(self, /) -> None:
                self._block._at_fork_reinit()
                self._count = 0
                self._owner = None

        def acquire(
            self,
            /,
            blocking: bool = True,
            timeout: float = -1,
        ) -> bool:
            thread = current_thread_ident()

            if self._owner == thread:
                if blocking and _checkpoints._threading_checkpoints_enabled():
                    _checkpoints._threading_checkpoint()

                self._count += 1

                return True

            success = self._block.acquire(blocking, timeout)

            if success:
                self._count = 1
                self._owner = thread

            return success

        def release(self, /) -> None:
            if self._owner != current_thread_ident():
                msg = "cannot release un-acquired lock"
                raise RuntimeError(msg)

            self._count -= 1

            if not self._count:
                self._owner = None
                self._block.release()

        if sys.version_info >= (3, 14):

            def locked(self, /) -> bool:
                return self._block.locked()

        # Internal methods used by condition variables

        def _acquire_restore(self, /, state: tuple[int, int]) -> None:
            self._block.acquire()
            self._count = state[0]
            self._owner = state[1]

        def _release_save(self, /) -> tuple[int, int]:
            if self._count == 0:
                msg = "cannot release un-acquired lock"
                raise RuntimeError(msg)

            state = (self._count, self._owner)

            self._count = 0
            self._owner = None
            self._block.release()

            return state

        def _is_owned(self, /) -> bool:
            return self._owner == current_thread_ident()

        # Internal method used for reentrancy checks

        if sys.version_info >= (3, 12, 1) or (
            sys.version_info < (3, 12) and sys.version_info >= (3, 11, 6)
        ):

            def _recursion_count(self, /) -> int:
                if self._owner == current_thread_ident():
                    return self._count
                else:
                    return 0


@final
class ThreadOnceLock:
    __slots__ = (
        "__weakref__",
        "_oncelock_count",
        "_oncelock_waiters",
    )

    _oncelock_count: int
    _oncelock_waiters: list[Any] | None

    def __init__(self, /) -> None:
        self._oncelock_count = 1
        self._oncelock_waiters = []

    def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn:
        bcs = ThreadOnceLock
        bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

        msg = f"type '{bcs_repr}' is not an acceptable base type"
        raise TypeError(msg)

    def __reduce__(self, /) -> NoReturn:
        msg = f"cannot reduce {self!r}"
        raise TypeError(msg)

    def __repr__(self, /) -> str:
        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        if _get_owner(self) is not None:
            status = "locked"
        else:
            status = "unlocked"

        object_repr = f"{status} {cls_repr} object"
        extra = f"owner={_get_owner(self)!r} count={_get_count(self)!r}"

        return f"<{object_repr} {extra} at {id(self):#x}>"

    def __enter__(self, /) -> bool:
        return self.acquire()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
        /,
    ) -> None:
        self.release()

    if sys.version_info >= (3, 9):

        def _at_fork_reinit(self, /) -> None:
            self._oncelock_count = 1
            self._oncelock_waiters = []

    def acquire(self, /, blocking: bool = True, timeout: float = -1) -> bool:
        if not self._oncelock_count:
            if blocking and _checkpoints._threading_checkpoints_enabled():
                _checkpoints._threading_checkpoint()

            return True

        thread = current_thread_ident()

        if _get_owner(self) == thread:
            if blocking and _checkpoints._threading_checkpoints_enabled():
                _checkpoints._threading_checkpoint()

            self._oncelock_count += 1

            return True

        waiters = self._oncelock_waiters

        if waiters is None:
            if blocking and _checkpoints._threading_checkpoints_enabled():
                _checkpoints._threading_checkpoint()

            return True

        waiters.append(token := [None, thread])

        if (owner := _get_owner(self)) is None or owner == thread:
            if blocking and _checkpoints._threading_checkpoints_enabled():
                _checkpoints._threading_checkpoint()

            return True

        block = create_thread_lock()
        block.acquire()

        token[0] = block

        if not self._oncelock_count:
            if blocking and _checkpoints._threading_checkpoints_enabled():
                _checkpoints._threading_checkpoint()

            return True

        return block.acquire(blocking, timeout)

    def release(self, /) -> None:
        maybe_acquired = self._oncelock_count

        if maybe_acquired:
            thread = current_thread_ident()

            if _get_owner(self) != thread:
                msg = "cannot release un-acquired lock"
                raise RuntimeError(msg)

            self._oncelock_count -= 1

            if self._oncelock_count:
                return

        if (waiters := self._oncelock_waiters) is not None:
            if maybe_acquired:
                waiters.reverse()

            while waiters:
                try:
                    block, _ = waiters.pop()
                except IndexError:
                    break
                else:
                    if block is not None:
                        block.release()

            self._oncelock_waiters = None

    if sys.version_info >= (3, 14):

        def locked(self, /) -> bool:
            return _get_owner(self) is not None

    # Internal methods used by condition variables

    def _acquire_restore(self, /, state: tuple[int, int]) -> None:
        if _checkpoints._threading_checkpoints_enabled():
            _checkpoints._threading_checkpoint()

    def _release_save(self, /) -> tuple[int, int]:
        if not self._oncelock_count:
            msg = "cannot release un-acquired lock"
            raise RuntimeError(msg)

        state = (_get_count(self), _get_owner(self))

        self._oncelock_count = 0

        if (waiters := self._oncelock_waiters) is not None:
            waiters.reverse()

            self.release()

        return state

    def _is_owned(self, /) -> bool:
        return _get_owner(self) == current_thread_ident()

    # Internal method used for reentrancy checks

    if sys.version_info >= (3, 12, 1) or (
        sys.version_info < (3, 12) and sys.version_info >= (3, 11, 6)
    ):

        def _recursion_count(self, /) -> int:
            count = self._oncelock_count

            if count and _get_owner(self) == current_thread_ident():
                return count

            return 0

    # Internal properties used for compatibility with threading._PyRLock

    @property
    def _block(self, /) -> ThreadLock:
        return create_thread_lock()

    @property
    def _count(self, /) -> int:
        count = self._oncelock_count

        if count and _get_owner(self) is not None:
            return count

        return 0

    @property
    def _owner(self, /) -> int | None:
        if waiters := self._oncelock_waiters:
            try:
                token = waiters[0]
            except IndexError:
                pass
            else:
                if self._oncelock_count:
                    return token[1]

        return None


_get_count = ThreadOnceLock._count.fget
_get_owner = ThreadOnceLock._owner.fget


@final
class ThreadDummyLock:
    __slots__ = ()

    def __new__(cls, /) -> ThreadDummyLock:
        return THREAD_DUMMY_LOCK

    def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn:
        bcs = ThreadDummyLock
        bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

        msg = f"type '{bcs_repr}' is not an acceptable base type"
        raise TypeError(msg)

    def __reduce__(self, /) -> str:
        return "THREAD_DUMMY_LOCK"

    def __copy__(self, /) -> ThreadDummyLock:
        return THREAD_DUMMY_LOCK

    def __repr__(self, /) -> str:
        return f"{self.__class__.__module__}.THREAD_DUMMY_LOCK"

    def __enter__(self, /) -> Literal[True]:
        if _checkpoints._threading_checkpoints_enabled():
            _checkpoints._threading_checkpoint()

        return True

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
        /,
    ) -> None:
        pass

    if sys.version_info >= (3, 9):

        def _at_fork_reinit(self, /) -> None:
            pass

    def acquire(
        self,
        /,
        blocking: bool = True,
        timeout: float = -1,
    ) -> Literal[True]:
        if blocking and _checkpoints._threading_checkpoints_enabled():
            _checkpoints._threading_checkpoint()

        return True

    def release(self, /) -> None:
        pass

    def locked(self, /) -> Literal[False]:
        return False

    # Internal methods used by condition variables

    def _acquire_restore(self, /, state: tuple[int, int]) -> None:
        if _checkpoints._threading_checkpoints_enabled():
            _checkpoints._threading_checkpoint()

    def _release_save(self, /) -> NoReturn:
        msg = "cannot release un-acquired lock"
        raise RuntimeError(msg)

    def _is_owned(self, /) -> Literal[False]:
        return False

    # Internal method used for reentrancy checks

    if sys.version_info >= (3, 12, 1) or (
        sys.version_info < (3, 12) and sys.version_info >= (3, 11, 6)
    ):

        def _recursion_count(self, /) -> Literal[0]:
            return 0

    # Internal properties used for compatibility with threading._PyRLock

    @property
    def _block(self, /) -> ThreadLock:
        return create_thread_lock()

    @property
    def _count(self, /) -> Literal[0]:
        return 0

    @property
    def _owner(self, /) -> None:
        return None


THREAD_DUMMY_LOCK: Final[ThreadDummyLock] = object.__new__(ThreadDummyLock)

if sys.version_info >= (3, 13):
    __allocate_lock = ThreadLock
else:
    __allocate_lock = import_original("_thread", "allocate_lock")


def create_thread_lock() -> ThreadLock:
    """
    Create a new instance of a primitive lock that blocks threads.

    The same as :class:`threading.Lock`, but not affected by monkey patching.
    """

    return __allocate_lock()


def create_thread_rlock() -> ThreadRLock:
    """
    Create a new instance of a reentrant lock that blocks threads.

    The same as :class:`threading.RLock`, but not affected by monkey patching.
    """

    return ThreadRLock()


def create_thread_oncelock() -> ThreadOnceLock:
    """
    Create a new instance of a once lock that mimics a reentrant lock but does
    nothing after release (when the counter reaches zero).

    It wakes up all threads at once, thereby solving the square problem, which
    makes it suitable for creating thread-safe initialization (or any other
    one-time actions).

    Unlike :class:`threading.RLock`, it is signal-safe.
    """

    return ThreadOnceLock()


@overload
def once(
    wrapped: MissingType = MISSING,
    /,
    *,
    reentrant: bool = False,
) -> Callable[[Callable[[], _T]], Callable[[], _T]]: ...
@overload
def once(wrapped: Callable[[], _T], /) -> Callable[[], _T]: ...
def once(wrapped=MISSING, /, *, reentrant=False):
    """
    Transform *wrapped* into a one-time function.

    Blocks threads attempting to execute the function in parallel and wakes
    them up at once upon completion. The result is stored in the closure of the
    new function and is returned on each subsequent call.

    Args:
      reentrant:
        Unless set to :data:`True`, recursive attempts to call the function
        will raise the :exc:`RuntimeError` exception. Also affects signal
        handlers and destructors.

    Raises:
      RuntimeError:
        if called recursively and ``reentrant=False``.
    """

    if wrapped is MISSING:
        return partial(once, reentrant=reentrant)

    lock = create_thread_oncelock()
    result = MISSING

    @wraps(wrapped)
    def wrapper():
        nonlocal lock
        nonlocal result

        if result is MISSING:
            with lock:
                if result is MISSING:
                    if not reentrant and lock._count > 1:
                        msg = "this function is already executing"
                        raise RuntimeError(msg)

                    result = wrapped()
                    lock = THREAD_DUMMY_LOCK

        return result

    return wrapper
