#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import warnings

from collections import deque
from copy import copy
from heapq import heapify, heappop, heappush
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    Protocol,
    TypeVar,
    Union,
    overload,
)

from ._semaphore import Semaphore
from .lowlevel import (
    MISSING,
    Event,
    MissingType,
    async_checkpoint,
    create_async_event,
    create_green_event,
    green_checkpoint,
)
from .lowlevel._utils import _copies as copies

if TYPE_CHECKING:
    import sys

    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self

    if sys.version_info >= (3, 9):
        from collections.abc import Callable, Iterable
    else:
        from typing import Callable, Iterable

_T = TypeVar("_T")
_T_contra = TypeVar("_T_contra", contravariant=True)


class _SupportsBool(Protocol):
    __slots__ = ()

    def __bool__(self, /) -> bool: ...


class _SupportsLT(Protocol[_T_contra]):
    __slots__ = ()

    def __lt__(self, other: _T_contra, /) -> _SupportsBool: ...


class _SupportsGT(Protocol[_T_contra]):
    __slots__ = ()

    def __gt__(self, other: _T_contra, /) -> _SupportsBool: ...


_RichComparableT = TypeVar(
    "_RichComparableT",
    bound=Union[_SupportsLT[Any], _SupportsGT[Any]],
)


class QueueEmpty(Exception):
    """..."""


class QueueFull(Exception):
    """..."""


class SimpleQueue(Generic[_T]):
    """..."""

    __slots__ = (
        "__weakref__",
        "_data",
        "_semaphore",
    )

    def __new__(cls, items: Iterable[_T] | MissingType = MISSING, /) -> Self:
        """..."""

        self = object.__new__(cls)

        if items is not MISSING:
            self._data = deque(items)
        else:
            self._data = deque()

        self._semaphore = Semaphore(len(self._data))

        return self

    def __getnewargs__(self, /) -> tuple[Any, ...]:
        """..."""

        return (tuple(copy(self._data)),)

    def __getstate__(self, /) -> None:
        """..."""

        return None

    def __repr__(self, /) -> str:
        """..."""

        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        items = list(copy(self._data))

        object_repr = f"{cls_repr}({items!r})"

        length = len(items)

        if length > 0:
            extra = f"length={length}"
        else:
            extra = f"length={length}, getting={self._semaphore.waiting}"

        return f"<{object_repr} at {id(self):#x} [{extra}]>"

    def __bool__(self, /) -> bool:
        """..."""

        return bool(self._data)

    def __len__(self) -> int:
        """..."""

        return len(self._data)

    def put(self, /, item: _T) -> None:
        """..."""

        self._data.append(item)
        self._semaphore.release()

    async def async_put(self, /, item: _T, *, blocking: bool = True) -> None:
        """..."""

        if blocking:
            await async_checkpoint()

        self._data.append(item)
        self._semaphore.async_release()

    def green_put(
        self,
        /,
        item: _T,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> None:
        """..."""

        if blocking:
            green_checkpoint()

        self._data.append(item)
        self._semaphore.green_release()

    async def async_get(self, /, *, blocking: bool = True) -> _T:
        """..."""

        success = await self._semaphore.async_acquire(blocking=blocking)

        if not success:
            raise QueueEmpty

        return self._data.popleft()

    def green_get(
        self,
        /,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> _T:
        """..."""

        success = self._semaphore.green_acquire(
            blocking=blocking,
            timeout=timeout,
        )

        if not success:
            raise QueueEmpty

        return self._data.popleft()

    @property
    def putting(self, /) -> int:
        """..."""

        return 0

    @property
    def getting(self, /) -> int:
        """..."""

        return self._semaphore.waiting

    @property
    def waiting(self, /) -> int:
        """..."""

        return self._semaphore.waiting


class SimpleLifoQueue(SimpleQueue[_T]):
    """..."""

    __slots__ = ()

    def __new__(cls, items: Iterable[_T] | MissingType = MISSING, /) -> Self:
        """..."""

        self = object.__new__(cls)

        if items is not MISSING:
            self._data = list(items)
        else:
            self._data = []

        self._semaphore = Semaphore(len(self._data))

        return self

    @copies(SimpleQueue.__getnewargs__)
    def __getnewargs__(self, /) -> tuple[Any, ...]:
        """..."""

        return SimpleQueue.__getnewargs__(self)

    @copies(SimpleQueue.__getstate__)
    def __getstate__(self, /) -> None:
        """..."""

        return SimpleQueue.__getstate__(self)

    @copies(SimpleQueue.__repr__)
    def __repr__(self, /) -> str:
        """..."""

        return SimpleQueue.__repr__(self)

    @copies(SimpleQueue.__bool__)
    def __bool__(self, /) -> bool:
        """..."""

        return SimpleQueue.__bool__(self)

    @copies(SimpleQueue.__len__)
    def __len__(self) -> int:
        """..."""

        return SimpleQueue.__len__(self)

    @copies(SimpleQueue.put)
    def put(self, /, item: _T) -> None:
        """..."""

        return SimpleQueue.put(self, item)

    @copies(SimpleQueue.async_put)
    async def async_put(self, /, item: _T, *, blocking: bool = True) -> None:
        """..."""

        return await SimpleQueue.async_put(self, item, blocking=blocking)

    @copies(SimpleQueue.green_put)
    def green_put(
        self,
        /,
        item: _T,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> None:
        """..."""

        return SimpleQueue.green_put(
            self,
            item,
            blocking=blocking,
            timeout=timeout,
        )

    async def async_get(self, /, *, blocking: bool = True) -> _T:
        """..."""

        success = await self._semaphore.async_acquire(blocking=blocking)

        if not success:
            raise QueueEmpty

        return self._data.pop()

    def green_get(
        self,
        /,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> _T:
        """..."""

        success = self._semaphore.green_acquire(
            blocking=blocking,
            timeout=timeout,
        )

        if not success:
            raise QueueEmpty

        return self._data.pop()

    @property
    @copies(SimpleQueue.putting.fget)
    def putting(self, /) -> int:
        """..."""

        return SimpleQueue.putting.fget(self)

    @property
    @copies(SimpleQueue.getting.fget)
    def getting(self, /) -> int:
        """..."""

        return SimpleQueue.getting.fget(self)

    @property
    @copies(SimpleQueue.waiting.fget)
    def waiting(self, /) -> int:
        """..."""

        return SimpleQueue.waiting.fget(self)


class Queue(Generic[_T]):
    """..."""

    __slots__ = (
        "__weakref__",
        "_data",
        "_getters",
        "_maxsize",
        "_putters",
        "_putters_and_getters",
        "_unlocked",
        "_waiters",
    )

    @overload
    def __new__(cls, /, maxsize: int | None = None) -> Self: ...
    @overload
    def __new__(
        cls,
        items: Iterable[_T] | MissingType = MISSING,
        /,
        maxsize: int | None = None,
    ) -> Self: ...
    def __new__(cls, items=MISSING, /, maxsize=None):
        """..."""

        if maxsize is None and (items is None or isinstance(items, int)):
            items, maxsize = MISSING, items

        if maxsize is None:
            maxsize = 0
        elif maxsize <= 0:
            warnings.warn(
                "Use maxsize=None instead",
                DeprecationWarning,
                stacklevel=2,
            )

        self = object.__new__(cls)

        if items is not MISSING:
            self._init(items, maxsize)
        else:
            self._init((), maxsize)

        self._unlocked = [None]

        self._putters = deque()
        self._putters_and_getters = deque()
        self._getters = deque()

        self._maxsize = maxsize

        return self

    def __getnewargs__(self, /) -> tuple[Any, ...]:
        """..."""

        if (maxsize := self._maxsize) != 0:
            return (tuple(copy(self._data)), maxsize)

        return (tuple(copy(self._data)),)

    def __getstate__(self, /) -> None:
        """..."""

        return None

    def __repr__(self, /) -> str:
        """..."""

        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        items = list(copy(self._data))

        maxsize = self._maxsize

        if maxsize > 0:
            object_repr = f"{cls_repr}({items!r}, maxsize={maxsize!r})"
        else:
            object_repr = f"{cls_repr}({items!r})"

        length = len(items)

        if length >= maxsize > 0:
            extra = f"length={length}, putting={len(self._putters)}"
        elif length > 0:
            extra = f"length={length}"
        else:
            extra = f"length={length}, getting={len(self._getters)}"

        return f"<{object_repr} at {id(self):#x} [{extra}]>"

    def __bool__(self, /) -> bool:
        """..."""

        return bool(self._data)

    def __len__(self) -> int:
        """..."""

        return len(self._data)

    def _acquire_nowait_on_putting(self, /) -> bool:
        if self._unlocked:
            if self._maxsize <= 0:
                try:
                    self._unlocked.pop()
                except IndexError:
                    return False
                else:
                    return True

            if len(self._data) < self._maxsize:
                try:
                    self._unlocked.pop()
                except IndexError:
                    return False
                else:
                    if len(self._data) < self._maxsize:
                        return True

                    self._release()

        return False

    def _acquire_nowait_on_getting(self, /) -> bool:
        if self._unlocked:
            if self._data:
                try:
                    self._unlocked.pop()
                except IndexError:
                    return False
                else:
                    if self._data:
                        return True

                    self._release()

        return False

    async def _async_acquire(
        self,
        /,
        acquire_nowait: Callable[[], bool],
        waiters: deque[Event],
        *,
        blocking: bool = True,
    ) -> bool:
        if acquire_nowait():
            if blocking:
                try:
                    await async_checkpoint()
                except BaseException:
                    self._release()
                    raise

            return True

        if not blocking:
            return False

        waiters.append(event := create_async_event())
        self._putters_and_getters.append(event)

        if acquire_nowait():
            length = len(self._data)

            if 0 >= length or length >= self._maxsize > 0:
                waiters.remove(event)
            else:
                self._putters_and_getters.remove(event)

            event.set()

        success = False

        try:
            try:
                success = await event
            finally:
                if success or not event.cancelled():
                    length = len(self._data)

                    if 0 >= length or length >= self._maxsize > 0:
                        self._putters_and_getters.remove(event)
                    else:
                        waiters.remove(event)
        finally:
            if not success:
                if event.cancelled():
                    try:
                        self._putters_and_getters.remove(event)
                    except ValueError:
                        pass

                    try:
                        waiters.remove(event)
                    except ValueError:
                        pass
                else:
                    self._release()

        return success

    def _green_acquire(
        self,
        /,
        acquire_nowait: Callable[[], bool],
        waiters: deque[Event],
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> bool:
        if acquire_nowait():
            if blocking:
                try:
                    green_checkpoint()
                except BaseException:
                    self._release()
                    raise

            return True

        if not blocking:
            return False

        waiters.append(event := create_green_event())
        self._putters_and_getters.append(event)

        if acquire_nowait():
            length = len(self._data)

            if 0 >= length or length >= self._maxsize > 0:
                waiters.remove(event)
            else:
                self._putters_and_getters.remove(event)

            event.set()

        success = False

        try:
            try:
                success = event.wait(timeout)
            finally:
                if success or not event.cancelled():
                    length = len(self._data)

                    if 0 >= length or length >= self._maxsize > 0:
                        self._putters_and_getters.remove(event)
                    else:
                        waiters.remove(event)
        finally:
            if not success:
                if event.cancelled():
                    try:
                        self._putters_and_getters.remove(event)
                    except ValueError:
                        pass

                    try:
                        waiters.remove(event)
                    except ValueError:
                        pass
                else:
                    self._release()

        return success

    async def async_put(self, /, item: _T, *, blocking: bool = True) -> None:
        """..."""

        acquired = await self._async_acquire(
            self._acquire_nowait_on_putting,
            self._putters,
            blocking=blocking,
        )

        if not acquired:
            raise QueueFull

        try:
            self._put(item)
        finally:
            self._release()

    def green_put(
        self,
        /,
        item: _T,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> None:
        """..."""

        acquired = self._green_acquire(
            self._acquire_nowait_on_putting,
            self._putters,
            blocking=blocking,
            timeout=timeout,
        )

        if not acquired:
            raise QueueFull

        try:
            self._put(item)
        finally:
            self._release()

    async def async_get(self, /, *, blocking: bool = True) -> _T:
        """..."""

        acquired = await self._async_acquire(
            self._acquire_nowait_on_getting,
            self._getters,
            blocking=blocking,
        )

        if not acquired:
            raise QueueEmpty

        try:
            return self._get()
        finally:
            self._release()

    def green_get(
        self,
        /,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> _T:
        """..."""

        acquired = self._green_acquire(
            self._acquire_nowait_on_getting,
            self._getters,
            blocking=blocking,
            timeout=timeout,
        )

        if not acquired:
            raise QueueEmpty

        try:
            return self._get()
        finally:
            self._release()

    def _release(self, /) -> None:
        while True:
            length = len(self._data)

            if length >= self._maxsize > 0:
                waiters = self._getters
            elif length > 0:
                waiters = self._putters_and_getters
            else:
                waiters = self._putters

            while waiters:
                try:
                    event = waiters.popleft()
                except IndexError:
                    pass
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

    def _init(self, /, items: Iterable[_T], maxsize: int) -> None:
        self._data = deque(items)

    def _put(self, /, item: _T) -> None:
        self._data.append(item)

    def _get(self, /) -> _T:
        return self._data.popleft()

    @property
    def maxsize(self, /) -> int:
        """..."""

        return self._maxsize

    @property
    def putting(self, /) -> int:
        """..."""

        return len(self._putters)

    @property
    def getting(self, /) -> int:
        """..."""

        return len(self._getters)

    @property
    def waiting(self, /) -> int:
        """..."""

        return len(self._putters_and_getters)


class LifoQueue(Queue[_T]):
    """..."""

    __slots__ = ()

    @overload
    def __new__(cls, /, maxsize: int | None = None) -> Self: ...
    @overload
    def __new__(
        cls,
        items: Iterable[_T] | MissingType = MISSING,
        /,
        maxsize: int | None = None,
    ) -> Self: ...
    @copies(Queue.__new__)
    def __new__(cls, items=MISSING, /, maxsize=None):
        """..."""

        return Queue.__new__(cls, items, maxsize)

    @copies(Queue.__getnewargs__)
    def __getnewargs__(self, /) -> tuple[Any, ...]:
        """..."""

        return Queue.__getnewargs__(self)

    @copies(Queue.__getstate__)
    def __getstate__(self, /) -> None:
        """..."""

        return Queue.__getstate__(self)

    @copies(Queue.__repr__)
    def __repr__(self, /) -> str:
        """..."""

        return Queue.__repr__(self)

    @copies(Queue.__bool__)
    def __bool__(self, /) -> bool:
        """..."""

        return Queue.__bool__(self)

    @copies(Queue.__len__)
    def __len__(self, /) -> bool:
        """..."""

        return Queue.__len__(self)

    @copies(Queue.async_put)
    async def async_put(self, /, item: _T, *, blocking: bool = True) -> None:
        """..."""

        return await Queue.async_put(self, item, blocking=blocking)

    @copies(Queue.green_put)
    def green_put(
        self,
        /,
        item: _T,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> None:
        """..."""

        return Queue.green_put(self, item, blocking=blocking, timeout=timeout)

    @copies(Queue.async_get)
    async def async_get(self, /, *, blocking: bool = True) -> _T:
        """..."""

        return await Queue.async_get(self, blocking=blocking)

    @copies(Queue.green_get)
    def green_get(
        self,
        /,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> _T:
        """..."""

        return Queue.green_get(self, blocking=blocking, timeout=timeout)

    def _init(self, /, items: Iterable[_T], maxsize: int) -> None:
        self._data = list(items)

    def _put(self, /, item: _T) -> None:
        self._data.append(item)

    def _get(self, /) -> _T:
        return self._data.pop()

    @property
    @copies(Queue.maxsize.fget)
    def maxsize(self, /) -> int:
        """..."""

        return Queue.maxsize.fget(self)

    @property
    @copies(Queue.putting.fget)
    def putting(self, /) -> int:
        """..."""

        return Queue.putting.fget(self)

    @property
    @copies(Queue.getting.fget)
    def getting(self, /) -> int:
        """..."""

        return Queue.getting.fget(self)

    @property
    @copies(Queue.waiting.fget)
    def waiting(self, /) -> int:
        """..."""

        return Queue.waiting.fget(self)


class PriorityQueue(Queue[_RichComparableT]):
    """..."""

    __slots__ = ()

    @overload
    def __new__(cls, /, maxsize: int | None = None) -> Self: ...
    @overload
    def __new__(
        cls,
        items: Iterable[_RichComparableT] | MissingType = MISSING,
        /,
        maxsize: int | None = None,
    ) -> Self: ...
    @copies(Queue.__new__)
    def __new__(cls, items=MISSING, /, maxsize=None):
        """..."""

        return Queue.__new__(cls, items, maxsize)

    @copies(Queue.__getnewargs__)
    def __getnewargs__(self, /) -> tuple[Any, ...]:
        """..."""

        return Queue.__getnewargs__(self)

    @copies(Queue.__getstate__)
    def __getstate__(self, /) -> None:
        """..."""

        return Queue.__getstate__(self)

    @copies(Queue.__repr__)
    def __repr__(self, /) -> str:
        """..."""

        return Queue.__repr__(self)

    @copies(Queue.__bool__)
    def __bool__(self, /) -> bool:
        """..."""

        return Queue.__bool__(self)

    @copies(Queue.__len__)
    def __len__(self, /) -> bool:
        """..."""

        return Queue.__len__(self)

    @copies(Queue.async_put)
    async def async_put(
        self,
        /,
        item: _RichComparableT,
        *,
        blocking: bool = True,
    ) -> None:
        """..."""

        return await Queue.async_put(self, item, blocking=blocking)

    @copies(Queue.green_put)
    def green_put(
        self,
        /,
        item: _RichComparableT,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> None:
        """..."""

        return Queue.green_put(self, item, blocking=blocking, timeout=timeout)

    @copies(Queue.async_get)
    async def async_get(self, /, *, blocking: bool = True) -> _RichComparableT:
        """..."""

        return await Queue.async_get(self, blocking=blocking)

    @copies(Queue.green_get)
    def green_get(
        self,
        /,
        *,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> _RichComparableT:
        """..."""

        return Queue.green_get(self, blocking=blocking, timeout=timeout)

    def _init(
        self,
        /,
        items: Iterable[_RichComparableT],
        maxsize: int,
    ) -> None:
        self._data = list(items)

        heapify(self._data)

    def _put(self, /, item: _RichComparableT) -> None:
        heappush(self._data, item)

    def _get(self, /) -> _RichComparableT:
        return heappop(self._data)

    @property
    @copies(Queue.maxsize.fget)
    def maxsize(self, /) -> int:
        """..."""

        return Queue.maxsize.fget(self)

    @property
    @copies(Queue.putting.fget)
    def putting(self, /) -> int:
        """..."""

        return Queue.putting.fget(self)

    @property
    @copies(Queue.getting.fget)
    def getting(self, /) -> int:
        """..."""

        return Queue.getting.fget(self)

    @property
    @copies(Queue.waiting.fget)
    def waiting(self, /) -> int:
        """..."""

        return Queue.waiting.fget(self)
