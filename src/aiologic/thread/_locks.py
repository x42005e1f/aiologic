#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from typing import TYPE_CHECKING

from aiologic.meta import SingletonEnum, import_original, replaces_with_outcome

from ._getters import current_thread_ident

if TYPE_CHECKING:
    from types import TracebackType
    from typing import Any, Final

    if sys.version_info >= (3, 9):
        from typing import Literal
    else:
        from typing_extensions import Literal

    if sys.version_info >= (3, 11):
        from typing import Never
    else:
        from typing_extensions import Never

if sys.version_info >= (3, 10):
    from typing import NewType
else:
    from typing_extensions import NewType

if sys.version_info >= (3, 11):
    from typing import final
else:
    from typing_extensions import final


@replaces_with_outcome(globals())
def _is_gil():
    try:
        from sys import _is_gil_enabled
    except ImportError:
        pass
    else:
        return _is_gil_enabled

    def impl():
        return True

    return impl


@replaces_with_outcome(globals())
def _is_tso():
    import platform

    answer = platform.machine().lower() in {
        "i386",
        "i686",
        "x86",
        "x86_64",
        "amd64",
        "s390x",
    }

    def impl():
        return answer

    return impl


@replaces_with_outcome(globals())
def _create_lock():
    return import_original("_thread", "allocate_lock")


@replaces_with_outcome(globals())
def _create_rlock():
    return import_original("_thread", "RLock")


RLockState = NewType("RLockState", "tuple[int, int]")
DummyLockState = NewType("DummyLockState", "tuple[int, int]")


@final
class LockType:
    __slots__ = (
        "__impl",
        "__weakref__",
    )

    def __init__(self, /) -> None:
        self.__impl = _create_lock()

    def __init_subclass__(cls, /, **kwargs: Any) -> Never:
        bcs = __class__
        bcs_name = bcs.__name__

        msg = f"type {bcs_name!r} is not an acceptable base type"
        raise TypeError(msg)

    def __reduce__(self, /) -> Never:
        cls = type(self)
        cls_name = cls.__name__

        msg = f"cannot pickle {cls_name!r} object"
        raise TypeError(msg)

    def __deepcopy__(self, memo: Any, /) -> Never:
        cls = type(self)
        cls_name = cls.__name__

        msg = f"cannot deep copy {cls_name!r} object"
        raise TypeError(msg)

    def __copy__(self, /) -> Never:
        cls = type(self)
        cls_name = cls.__name__

        msg = f"cannot copy {cls_name!r} object"
        raise TypeError(msg)

    def __repr__(self, /) -> str:
        cls = type(self)
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        result = repr(self.__impl)
        result = result.replace("_thread.lock", cls_repr)
        result = result.replace(f"{id(self.__impl):#x}", f"{id(self):#x}")

        return result

    def __enter__(self, /) -> bool:
        return self.__impl.acquire()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
        /,
    ) -> None:
        self.__impl.release()

    def acquire(self, /, blocking: bool = True, timeout: float = -1) -> bool:
        return self.__impl.acquire(blocking, timeout)

    def release(self, /) -> None:
        self.__impl.release()

    def locked(self, /) -> bool:
        return self.__impl.locked()

    def _at_fork_reinit(self, /) -> None:
        impl = self.__impl

        try:
            method = impl._at_fork_reinit
        except AttributeError:
            try:
                impl.release()
            except RuntimeError:
                pass
        else:
            method()


@final
class RLockType:
    __slots__ = (
        "__impl",
        "__weakref__",
    )

    def __init__(self, /) -> None:
        self.__impl = _create_rlock()

    def __init_subclass__(cls, /, **kwargs: Any) -> Never:
        bcs = __class__
        bcs_name = bcs.__name__

        msg = f"type {bcs_name!r} is not an acceptable base type"
        raise TypeError(msg)

    def __reduce__(self, /) -> Never:
        cls = type(self)
        cls_name = cls.__name__

        msg = f"cannot pickle {cls_name!r} object"
        raise TypeError(msg)

    def __deepcopy__(self, memo: Any, /) -> Never:
        cls = type(self)
        cls_name = cls.__name__

        msg = f"cannot deep copy {cls_name!r} object"
        raise TypeError(msg)

    def __copy__(self, /) -> Never:
        cls = type(self)
        cls_name = cls.__name__

        msg = f"cannot copy {cls_name!r} object"
        raise TypeError(msg)

    def __repr__(self, /) -> str:
        cls = type(self)
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        result = repr(self.__impl)
        result = result.replace("_thread.RLock", cls_repr)
        result = result.replace(f"{id(self.__impl):#x}", f"{id(self):#x}")

        return result

    def __enter__(self, /) -> bool:
        return self.__impl.acquire()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
        /,
    ) -> None:
        self.__impl.release()

    def acquire(self, /, blocking: bool = True, timeout: float = -1) -> bool:
        return self.__impl.acquire(blocking, timeout)

    def release(self, /) -> None:
        self.__impl.release()

    def locked(self, /) -> bool:
        impl = self.__impl

        try:
            method = impl.locked
        except AttributeError:
            if impl._is_owned():
                return True

            if impl.acquire(False):
                impl.release()

                return False

            return True
        else:
            return method()

    def _is_owned(self, /) -> bool:
        return self.__impl._is_owned()

    def _recursion_count(self, /) -> int:
        impl = self.__impl

        try:
            method = impl._recursion_count
        except AttributeError:
            if impl._is_owned():
                count, owner = state = impl._release_save()

                impl._acquire_restore(state)

                return count

            return 0
        else:
            return method()

    def _acquire_restore(self, state: RLockState, /) -> None:
        self.__impl._acquire_restore(state)

    def _release_save(self, /) -> RLockState:
        return self.__impl._release_save()

    def _at_fork_reinit(self, /) -> None:
        impl = self.__impl

        try:
            method = impl._at_fork_reinit
        except AttributeError:
            try:
                impl._release_save()
            except RuntimeError:
                pass
        else:
            method()


@final
class DummyLockType(SingletonEnum):
    DUMMY_LOCK = "DUMMY_LOCK"

    def __init_subclass__(cls, /, **kwargs: Any) -> Never:
        bcs = __class__
        bcs_name = bcs.__name__

        msg = f"type {bcs_name!r} is not an acceptable base type"
        raise TypeError(msg)

    def __enter__(self, /) -> Literal[True]:
        return True

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
        /,
    ) -> None:
        pass

    def acquire(
        self,
        /,
        blocking: bool = True,
        timeout: float = -1,
    ) -> Literal[True]:
        return True

    def release(self, /) -> None:
        pass

    def locked(self, /) -> Literal[False]:
        return False

    def _is_owned(self, /) -> Literal[False]:
        return False

    def _recursion_count(self, /) -> Literal[0]:
        return 0

    def _acquire_restore(self, state: DummyLockState, /) -> None:
        count, owner = state

    def _release_save(self, /) -> DummyLockState:
        return (0, current_thread_ident())

    def _at_fork_reinit(self, /) -> None:
        pass


DUMMY_LOCK: Final[Literal[DummyLockType.DUMMY_LOCK]] = DummyLockType.DUMMY_LOCK


def create_lock() -> LockType:
    return LockType()


def create_rlock() -> RLockType:
    return RLockType()


def create_rlock_if_nogil() -> RLockType | DummyLockType:
    if _is_gil():
        return DUMMY_LOCK
    else:
        return RLockType()


def create_rlock_if_notso() -> RLockType | DummyLockType:
    if _is_gil() or _is_tso():
        return DUMMY_LOCK
    else:
        return RLockType()
