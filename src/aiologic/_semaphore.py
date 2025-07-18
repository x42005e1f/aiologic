#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import os
import platform
import sys

from collections import deque
from typing import TYPE_CHECKING, Any, Final, overload

from .lowlevel import (
    Event,
    async_checkpoint,
    create_async_event,
    create_green_event,
    green_checkpoint,
)

if TYPE_CHECKING:
    from types import TracebackType

    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self

__PYTHON_IMPLEMENTATION = platform.python_implementation()

try:
    from sys import _is_gil_enabled
except ImportError:
    __GIL_ENABLED: Final[bool] = True
else:
    __GIL_ENABLED: Final[bool] = _is_gil_enabled()

_USE_DELATTR: Final[bool] = (
    __GIL_ENABLED or sys.version_info >= (3, 14)  # see python/cpython#127266
)
_USE_BYTEARRAY: Final[bool] = __PYTHON_IMPLEMENTATION == "CPython" and (
    __GIL_ENABLED or sys.version_info >= (3, 14)  # see python/cpython#129107
)

_PERFECT_FAIRNESS_ENABLED: Final[bool] = bool(
    os.getenv(
        "AIOLOGIC_PERFECT_FAIRNESS",
        "1" if __GIL_ENABLED else "",
    )
)


class Semaphore:
    __slots__ = (
        "__weakref__",
        "_initial_value",
        "_unlocked",
        "_waiters",
    )

    @overload
    def __new__(
        cls,
        /,
        initial_value: int | None = None,
        max_value: None = None,
    ) -> Self: ...
    @overload
    def __new__(
        cls,
        /,
        initial_value: int | None,
        max_value: int,
    ) -> BoundedSemaphore: ...
    @overload
    def __new__(cls, /, *, max_value: int) -> BoundedSemaphore: ...
    def __new__(cls, /, initial_value=None, max_value=None):
        if max_value is not None:
            if cls is not Semaphore:
                msg = (
                    "max_value must be None for subclasses."
                    " Did you want to inherit BoundedSemaphore instead?"
                )
                raise TypeError(msg)

            return BoundedSemaphore.__new__(
                BoundedSemaphore,
                initial_value,
                max_value,
            )

        self = object.__new__(cls)

        if initial_value is not None:
            if initial_value < 0:
                msg = "initial_value must be >= 0"
                raise ValueError(msg)

            self._initial_value = initial_value
        else:
            self._initial_value = 1

        if _USE_BYTEARRAY:
            self._unlocked = bytearray(self._initial_value)
        else:
            self._unlocked = [None] * self._initial_value

        self._waiters = deque()

        return self

    def __getnewargs__(self, /) -> tuple[Any, ...]:
        if (initial_value := self._initial_value) != 1:
            return (initial_value,)

        return ()

    def __getstate__(self, /) -> None:
        return None

    def __repr__(self, /) -> str:
        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        object_repr = f"{cls_repr}({self._initial_value!r})"

        value = len(self._unlocked)

        if value > 0:
            extra = f"value={value}"
        else:
            extra = f"value={value}, waiting={len(self._waiters)}"

        return f"<{object_repr} at {id(self):#x} [{extra}]>"

    async def __aenter__(self, /) -> Self:
        await self.async_acquire()

        return self

    def __enter__(self, /) -> Self:
        self.green_acquire()

        return self

    async def __aexit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.async_release()

    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.green_release()

    def _acquire_nowait(self, /) -> bool:
        if self._unlocked:
            try:
                self._unlocked.pop()
            except IndexError:
                return False
            else:
                return True

        return False

    async def async_acquire(
        self,
        /,
        *,
        blocking: bool = True,
        _shield: bool = False,
    ) -> bool:
        if self._acquire_nowait():
            if blocking:
                try:
                    await async_checkpoint()
                except BaseException:
                    self._release()
                    raise

            return True

        if not blocking:
            return False

        self._waiters.append(event := create_async_event(shield=_shield))

        if self._acquire_nowait():
            if event.set():
                try:
                    self._waiters.remove(event)
                except ValueError:
                    pass
            else:
                self._release()

        success = False

        try:
            success = await event
        finally:
            if not success:
                if event.cancelled():
                    try:
                        self._waiters.remove(event)
                    except ValueError:
                        pass
                else:
                    self._release()

        return success

    def green_acquire(
        self,
        /,
        *,
        blocking: bool = True,
        timeout: float | None = None,
        _shield: bool = False,
    ) -> bool:
        if self._acquire_nowait():
            if blocking:
                try:
                    green_checkpoint()
                except BaseException:
                    self._release()
                    raise

            return True

        if not blocking:
            return False

        self._waiters.append(event := create_green_event(shield=_shield))

        if self._acquire_nowait():
            if event.set():
                try:
                    self._waiters.remove(event)
                except ValueError:
                    pass
            else:
                self._release()

        success = False

        try:
            success = event.wait(timeout)
        finally:
            if not success:
                if event.cancelled():
                    try:
                        self._waiters.remove(event)
                    except ValueError:
                        pass
                else:
                    self._release()

        return success

    def release(self, /, count: int = 1) -> None:
        waiters = self._waiters

        while True:
            while waiters and count:
                try:
                    if _PERFECT_FAIRNESS_ENABLED:
                        event = waiters[0]
                    else:
                        event = waiters.popleft()
                except IndexError:
                    break
                else:
                    if event.set():
                        count -= 1

                    if _PERFECT_FAIRNESS_ENABLED:
                        try:
                            waiters.remove(event)
                        except ValueError:
                            pass

            if count < 1:
                break
            elif count == 1:
                if _USE_BYTEARRAY:
                    self._unlocked.append(0)
                else:
                    self._unlocked.append(None)
            else:
                if _USE_BYTEARRAY:
                    self._unlocked.extend(b"\x00" * count)
                else:
                    self._unlocked.extend([None] * count)

            if waiters:
                try:
                    self._unlocked.pop()
                except IndexError:
                    break
                else:
                    count = 1
            else:
                break

    async_release = release
    green_release = release

    _async_acquire = async_acquire
    _green_acquire = green_acquire

    _release = release

    @property
    def initial_value(self, /) -> int:
        return self._initial_value

    @property
    def value(self, /) -> int:
        return len(self._unlocked)

    @property
    def waiting(self, /) -> int:
        return len(self._waiters)


class BoundedSemaphore(Semaphore):
    __slots__ = (
        "_locked",
        "_max_value",
    )

    @overload
    def __new__(
        cls,
        /,
        initial_value: int | None = None,
        max_value: None = None,
    ) -> Self: ...
    @overload
    def __new__(
        cls,
        /,
        initial_value: int | None,
        max_value: int,
    ) -> Self: ...
    @overload
    def __new__(cls, /, *, max_value: int) -> Self: ...
    def __new__(cls, /, initial_value=None, max_value=None):
        if (
            cls is BoundedSemaphore
            and (initial_value is None or initial_value <= 1)
            and (max_value is None or max_value <= 1)
        ):
            return BoundedBinarySemaphore.__new__(
                BoundedBinarySemaphore,
                initial_value,
                max_value,
            )

        self = object.__new__(cls)

        if initial_value is not None:
            if initial_value < 0:
                msg = "initial_value must be >= 0"
                raise ValueError(msg)

            self._initial_value = initial_value
        elif max_value is not None:
            self._initial_value = max_value
        else:
            self._initial_value = 1

        if max_value is not None:
            if max_value < 0:
                msg = "max_value must be >= 0"
                raise ValueError(msg)

            if max_value < self._initial_value:
                msg = "max_value must be >= initial_value"
                raise ValueError(msg)

            self._max_value = max_value
        else:
            self._max_value = self._initial_value

        if _USE_BYTEARRAY:
            self._locked = bytearray(self._max_value - self._initial_value)
            self._unlocked = bytearray(self._initial_value)
        else:
            self._locked = [None] * (self._max_value - self._initial_value)
            self._unlocked = [None] * self._initial_value

        self._waiters = deque()

        return self

    def __getnewargs__(self, /) -> tuple[Any, ...]:
        initial_value = self._initial_value
        max_value = self._max_value

        if initial_value != max_value:
            return (initial_value, max_value)

        if initial_value != 1:
            return (initial_value,)

        return ()

    def __getstate__(self, /) -> None:
        return None

    def __repr__(self, /) -> str:
        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        initial_value = self._initial_value
        max_value = self._max_value

        if initial_value != max_value:
            args_repr = f"{initial_value!r}, max_value={max_value!r}"
        else:
            args_repr = f"{initial_value!r}"

        object_repr = f"{cls_repr}({args_repr})"

        value = len(self._unlocked)

        if value > 0:
            extra = f"value={value}"
        else:
            extra = f"value={value}, waiting={len(self._waiters)}"

        return f"<{object_repr} at {id(self):#x} [{extra}]>"

    async def async_acquire(
        self,
        /,
        *,
        blocking: bool = True,
        _shield: bool = False,
    ) -> bool:
        success = await self._async_acquire(blocking=blocking, _shield=_shield)

        if success:
            if _USE_BYTEARRAY:
                self._locked.append(0)
            else:
                self._locked.append(None)

        return success

    def green_acquire(
        self,
        /,
        *,
        blocking: bool = True,
        timeout: float | None = None,
        _shield: bool = False,
    ) -> bool:
        success = self._green_acquire(
            blocking=blocking,
            timeout=timeout,
            _shield=_shield,
        )

        if success:
            if _USE_BYTEARRAY:
                self._locked.append(0)
            else:
                self._locked.append(None)

        return success

    def release(self, /, count: int = 1) -> None:
        if count != 1:
            msg = "count must be 1"
            raise ValueError(msg)

        try:
            self._locked.pop()
        except IndexError:
            msg = "semaphore released too many times"
            raise RuntimeError(msg) from None

        self._release(count)

    async_release = release
    green_release = release

    @property
    def max_value(self, /) -> int:
        return self._max_value

    @property
    def value(self, /) -> int:
        return len(self._unlocked)


class BinarySemaphore(Semaphore):
    __slots__ = ()

    @overload
    def __new__(
        cls,
        /,
        initial_value: int | None = None,
        max_value: None = None,
    ) -> Self: ...
    @overload
    def __new__(
        cls,
        /,
        initial_value: int | None,
        max_value: int,
    ) -> BoundedBinarySemaphore: ...
    @overload
    def __new__(cls, /, *, max_value: int) -> BoundedBinarySemaphore: ...
    def __new__(cls, /, initial_value=None, max_value=None):
        if max_value is not None:
            if cls is not BinarySemaphore:
                msg = (
                    "max_value must be None for subclasses."
                    " Did you want to inherit BoundedBinarySemaphore instead?"
                )
                raise TypeError(msg)

            return BoundedBinarySemaphore.__new__(
                BoundedBinarySemaphore,
                initial_value,
                max_value,
            )

        self = object.__new__(cls)

        if initial_value is not None:
            if initial_value < 0 or 1 < initial_value:
                msg = "initial_value must be 0 or 1"
                raise ValueError(msg)

            self._initial_value = initial_value
        else:
            self._initial_value = 1

        self._unlocked = [None] * self._initial_value

        self._waiters = deque()

        return self

    def release(self, /, count: int = 1) -> None:
        if count != 1:
            msg = "count must be 1"
            raise ValueError(msg)

        self._release(count)

    async_release = release
    green_release = release

    def _release(self, /, count: int = 1) -> None:
        waiters = self._waiters

        while True:
            while waiters:
                try:
                    event = waiters.popleft()
                except IndexError:
                    break
                else:
                    if event.set():
                        return

            self._unlocked.append(None)

            if waiters:
                try:
                    self._unlocked.pop()
                except IndexError:
                    break
            else:
                break

    @property
    def value(self, /) -> int:
        return len(self._unlocked)

    # Internal methods used by condition variables

    def _park(self, /, token: list[Any]) -> bool:
        event = token[0]

        if event.cancelled():
            return False

        self._waiters.append(event)

        token[5] = True  # reparked

        if event.cancelled():
            try:
                self._waiters.remove(event)
            except ValueError:
                pass

            return False

        return True

    def _unpark(self, /, event: Event) -> None:
        try:
            self._waiters.remove(event)
        except ValueError:
            pass

    def _after_park(self, /) -> None:
        pass


class BoundedBinarySemaphore(BinarySemaphore, BoundedSemaphore):
    __slots__ = ()

    @overload
    def __new__(
        cls,
        /,
        initial_value: int | None = None,
        max_value: None = None,
    ) -> Self: ...
    @overload
    def __new__(
        cls,
        /,
        initial_value: int | None,
        max_value: int,
    ) -> Self: ...
    @overload
    def __new__(cls, /, *, max_value: int) -> Self: ...
    def __new__(cls, /, initial_value=None, max_value=None):
        self = object.__new__(cls)

        if initial_value is not None:
            if initial_value < 0 or 1 < initial_value:
                msg = "initial_value must be 0 or 1"
                raise ValueError(msg)

            self._initial_value = initial_value
        elif max_value is not None:
            self._initial_value = max_value
        else:
            self._initial_value = 1

        if max_value is not None:
            if max_value < 0 or 1 < max_value:
                msg = "max_value must be 0 or 1"
                raise ValueError(msg)

            if max_value < self._initial_value:
                msg = "max_value must be >= initial_value"
                raise ValueError(msg)

            self._max_value = max_value
        else:
            self._max_value = self._initial_value

        if _USE_DELATTR:
            if self._max_value > self._initial_value:
                self._locked = True
        else:
            self._locked = [None] * (self._max_value - self._initial_value)

        self._unlocked = [None] * self._initial_value

        self._waiters = deque()

        return self

    __getnewargs__ = BoundedSemaphore.__getnewargs__
    __getstate__ = BoundedSemaphore.__getstate__
    __repr__ = BoundedSemaphore.__repr__

    async def async_acquire(
        self,
        /,
        *,
        blocking: bool = True,
        _shield: bool = False,
    ) -> bool:
        success = await self._async_acquire(blocking=blocking, _shield=_shield)

        if success:
            if _USE_DELATTR:
                self._locked = True
            else:
                self._locked.append(None)

        return success

    def green_acquire(
        self,
        /,
        *,
        blocking: bool = True,
        timeout: float | None = None,
        _shield: bool = False,
    ) -> bool:
        success = self._green_acquire(
            blocking=blocking,
            timeout=timeout,
            _shield=_shield,
        )

        if success:
            if _USE_DELATTR:
                self._locked = True
            else:
                self._locked.append(None)

        return success

    def release(self, /, count: int = 1) -> None:
        if count != 1:
            msg = "count must be 1"
            raise ValueError(msg)

        try:
            if _USE_DELATTR:
                del self._locked
            else:
                self._locked.pop()
        except (AttributeError, IndexError):
            msg = "semaphore released too many times"
            raise RuntimeError(msg) from None

        self._release(count)

    async_release = release
    green_release = release

    @property
    def value(self, /) -> int:
        return len(self._unlocked)

    # Internal methods used by condition variables

    def _after_park(self, /) -> None:
        if _USE_DELATTR:
            self._locked = True
        else:
            self._locked.append(None)
