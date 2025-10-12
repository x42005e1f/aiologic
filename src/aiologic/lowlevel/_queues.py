#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from collections import deque
from functools import wraps
from typing import TYPE_CHECKING, Any, ClassVar, Final, SupportsIndex, TypeVar

from ._locks import ThreadOnceLock
from ._markers import DEFAULT, MISSING, DefaultType, MissingType

if sys.version_info >= (3, 9):
    from collections.abc import Iterable, Iterator, MutableSequence
else:
    from typing import Iterable, Iterator, MutableSequence

if TYPE_CHECKING:
    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self

try:
    from sys import _is_gil_enabled
except ImportError:
    __GIL_ENABLED: Final[bool] = True
else:
    __GIL_ENABLED: Final[bool] = _is_gil_enabled()

_USE_ONCELOCK: Final[bool] = not __GIL_ENABLED

_WRAPPER_ASSIGNMENTS: tuple[str, ...] = (
    "__doc__",
    "__annotate__",
    "__type_params__",
)

_T = TypeVar("_T")


class lazydeque(MutableSequence[_T]):
    __slots__ = (
        "__weakref__",
        "_data",
        "_data_holder",
        "_maxlen",
    )

    if _USE_ONCELOCK:
        __slots__ = tuple(dict.fromkeys(__slots__ + ThreadOnceLock.__slots__))

    def __new__(
        cls,
        /,
        iterable: Iterable[_T] | MissingType = MISSING,
        maxlen: int | None = None,
    ) -> Self:
        self = object.__new__(cls)

        self._data = None

        if _USE_ONCELOCK:
            self._data_holder = None

            ThreadOnceLock.__init__(self)
        else:
            self._data_holder = []

        self._maxlen = maxlen

        if iterable is not MISSING:
            self += iterable

        return self

    def __getnewargs__(self, /) -> tuple[Any, ...]:
        if (data := self._data) is not None:
            return (tuple(data.copy()), self._maxlen)

        return ((), self._maxlen)

    def __getstate__(self, /) -> None:
        return None

    def __copy__(self, /) -> Self:
        if (data := self._data) is not None:
            return self.__class__(data.copy(), self._maxlen)

        return self.__class__(maxlen=self._maxlen)

    def __repr__(self, /) -> str:
        if (data := self._data) is not None:
            data_repr = repr(data).rpartition("(")[2].partition(")")[0]
        else:
            data_repr = "[]"

        return f"{self.__class__.__qualname__}({data_repr})"

    __hash__: ClassVar[None] = None  # type: ignore[assignment]

    def __eq__(self, value: object, /) -> bool:
        if self is value:
            return True

        if isinstance(value, lazydeque):
            value_was_lazydeque = True

            value = value._data
        else:
            value_was_lazydeque = False

        if value_was_lazydeque or isinstance(value, deque):
            data = self._data

            if data and value:
                return data == value
            else:
                return not (data or value)

        return NotImplemented

    def __ne__(self, value: object, /) -> bool:
        if self is value:
            return False

        if isinstance(value, lazydeque):
            value_was_lazydeque = True

            value = value._data
        else:
            value_was_lazydeque = False

        if value_was_lazydeque or isinstance(value, deque):
            data = self._data

            if data and value:
                return data != value
            else:
                return bool(data or value)

        return NotImplemented

    def __lt__(self, value: lazydeque[_T] | deque[_T], /) -> bool:
        if self is value:
            return False

        if isinstance(value, lazydeque):
            value_was_lazydeque = True

            value = value._data
        else:
            value_was_lazydeque = False

        if value_was_lazydeque or isinstance(value, deque):
            data = self._data

            if data and value:
                return data < value
            else:
                return bool(value)

        return NotImplemented

    def __le__(self, value: lazydeque[_T] | deque[_T], /) -> bool:
        if self is value:
            return True

        if isinstance(value, lazydeque):
            value_was_lazydeque = True

            value = value._data
        else:
            value_was_lazydeque = False

        if value_was_lazydeque or isinstance(value, deque):
            data = self._data

            if data and value:
                return data <= value
            else:
                return not data

        return NotImplemented

    def __gt__(self, value: lazydeque[_T] | deque[_T], /) -> bool:
        if self is value:
            return False

        if isinstance(value, lazydeque):
            value_was_lazydeque = True

            value = value._data
        else:
            value_was_lazydeque = False

        if value_was_lazydeque or isinstance(value, deque):
            data = self._data

            if data and value:
                return data > value
            else:
                return bool(data)

        return NotImplemented

    def __ge__(self, value: lazydeque[_T] | deque[_T], /) -> bool:
        if self is value:
            return True

        if isinstance(value, lazydeque):
            value_was_lazydeque = True

            value = value._data
        else:
            value_was_lazydeque = False

        if value_was_lazydeque or isinstance(value, deque):
            data = self._data

            if data and value:
                return data >= value
            else:
                return not value

        return NotImplemented

    def __add__(self, value: lazydeque[_T] | deque[_T], /) -> Self:
        if self is value:
            if (data := self._data) is not None:
                return self.__class__(data + data, self._maxlen)

            return self.__class__(maxlen=self._maxlen)

        if isinstance(value, lazydeque):
            value_was_lazydeque = True

            value = value._data
        else:
            value_was_lazydeque = False

        if value_was_lazydeque or isinstance(value, deque):
            data = self._data

            if data and value:
                return self.__class__(data + value, self._maxlen)
            elif data:
                return self.__class__(data, self._maxlen)
            elif value:
                return self.__class__(value, self._maxlen)
            else:
                return self.__class__(maxlen=self._maxlen)

        return NotImplemented

    def __radd__(self, value: lazydeque[_T] | deque[_T], /) -> Self:
        if self is value:
            if (data := self._data) is not None:
                return self.__class__(data + data, self._maxlen)

            return self.__class__(maxlen=self._maxlen)

        if isinstance(value, lazydeque):
            value_was_lazydeque = True

            value = value._data
        else:
            value_was_lazydeque = False

        if value_was_lazydeque or isinstance(value, deque):
            data = self._data

            if data and value:
                return self.__class__(data + value, self._maxlen)
            elif data:
                return self.__class__(data, self._maxlen)
            elif value:
                return self.__class__(value, self._maxlen)
            else:
                return self.__class__(maxlen=self._maxlen)

        return NotImplemented

    def __mul__(self, value: SupportsIndex, /) -> Self:
        if (data := self._data) is not None:
            return self.__class__(data * value, self._maxlen)

        if not isinstance(value, int):
            "" * value  # checks for isinstance(value, SupportsIndex)

        return self.__class__(maxlen=self._maxlen)

    def __rmul__(self, value: SupportsIndex, /) -> Self:
        if (data := self._data) is not None:
            return self.__class__(value * data, self._maxlen)

        if not isinstance(value, int):
            "" * value  # checks for isinstance(value, SupportsIndex)

        return self.__class__(maxlen=self._maxlen)

    def __iadd__(self, value: Iterable[_T], /) -> Self:
        if self is value:
            if (data := self._data) is not None:
                data += data

            return self

        if isinstance(value, lazydeque):
            value = value._data

            if value:
                data = self._data

                if data is None:
                    data = self._init()

                data += value

            return self

        data = self._data

        if data is None:
            empty = not value

            if empty and not isinstance(value, deque):
                value = tuple(value)  # checks for isinstance(value, Iterable)

                empty = not value

            if not empty:
                data = self._init()
                data += value
        else:
            data += value

        return self

    def __imul__(self, value: SupportsIndex, /) -> Self:
        if (data := self._data) is not None:
            data *= value
            return self

        if not isinstance(value, int):
            "" * value  # checks for isinstance(value, SupportsIndex)

        return self

    def __getitem__(  # type: ignore[override]
        self,
        key: SupportsIndex,
        /,
    ) -> _T:
        if (data := self._data) is not None:
            return data[key]

        if not isinstance(key, int):
            range(key)  # checks for isinstance(key, SupportsIndex)

        msg = "deque index out of range"
        raise IndexError(msg)

    def __setitem__(  # type: ignore[override]
        self,
        key: SupportsIndex,
        value: _T,
        /,
    ) -> None:
        if (data := self._data) is not None:
            data[key] = value

        if not isinstance(key, int):
            range(key)  # checks for isinstance(key, SupportsIndex)

        msg = "deque index out of range"
        raise IndexError(msg)

    def __delitem__(  # type: ignore[override]
        self,
        key: SupportsIndex,
        /,
    ) -> None:
        if (data := self._data) is not None:
            del data[key]

        if not isinstance(key, int):
            range(key)  # checks for isinstance(key, SupportsIndex)

        msg = "deque index out of range"
        raise IndexError(msg)

    def __contains__(self, key: object, /) -> bool:
        if (data := self._data) is not None:
            return key in data

        return False

    def __bool__(self, /) -> bool:
        if (data := self._data) is not None:
            return bool(data)

        return False

    def __len__(self, /) -> int:
        if (data := self._data) is not None:
            return len(data)

        return 0

    def __iter__(self, /) -> Iterator[_T]:
        if (data := self._data) is not None:
            return iter(data)

        return self._iter()

    def __reversed__(self, /) -> Iterator[_T]:
        if (data := self._data) is not None:
            return reversed(data)

        return self._reversed()

    if _USE_ONCELOCK:

        def _init(self, /) -> deque[_T]:
            ThreadOnceLock.acquire(self)

            try:
                if self._data is None:
                    data_holder = self._data_holder

                    if data_holder is None:
                        self._data_holder = data_holder = []

                    data_holder.append(deque(maxlen=self._maxlen))

                    if self._data is None:
                        self._data = data_holder[0]

                    self._data_holder = None
            finally:
                ThreadOnceLock.release(self)

            return self._data

    else:

        def _init(self, /) -> deque[_T]:
            if (data_holder := self._data_holder) is not None:
                if not data_holder:
                    data_holder.append(deque(maxlen=self._maxlen))

                self._data = data_holder[0]
                self._data_holder = None

            return self._data

    def _iter(self, /) -> Iterator[_T]:
        if (data := self._data) is not None:
            return (yield from iter(data))

    def _reversed(self, /) -> Iterator[_T]:
        if (data := self._data) is not None:
            return (yield from reversed(data))

    @wraps(deque.copy, assigned=_WRAPPER_ASSIGNMENTS)
    def copy(self, /) -> Self:
        return self.__copy__()

    @wraps(deque.append, assigned=_WRAPPER_ASSIGNMENTS)
    def append(self, x: _T, /) -> None:
        data = self._data

        if data is None:
            data = self._init()

        return data.append(x)

    @wraps(deque.appendleft, assigned=_WRAPPER_ASSIGNMENTS)
    def appendleft(self, x: _T, /) -> None:
        data = self._data

        if data is None:
            data = self._init()

        return data.appendleft(x)

    @wraps(deque.extend, assigned=_WRAPPER_ASSIGNMENTS)
    def extend(self, iterable: Iterable[_T], /) -> None:
        value = iterable

        if self is value:
            if (data := self._data) is not None:
                data.extend(data)

            return

        if isinstance(value, lazydeque):
            value = value._data

            if value:
                data = self._data

                if data is None:
                    data = self._init()

                data.extend(value)

            return

        data = self._data

        if data is None:
            empty = not value

            if empty and not isinstance(value, deque):
                value = tuple(value)  # checks for isinstance(value, Iterable)

                empty = not value

            if not empty:
                data = self._init()
                data.extend(value)
        else:
            data.extend(value)

    @wraps(deque.extendleft, assigned=_WRAPPER_ASSIGNMENTS)
    def extendleft(self, iterable: Iterable[_T], /) -> None:
        value = iterable

        if self is value:
            if (data := self._data) is not None:
                data.extendleft(data)

            return

        if isinstance(value, lazydeque):
            value = value._data

            if value:
                data = self._data

                if data is None:
                    data = self._init()

                data.extendleft(value)

            return

        data = self._data

        if data is None:
            empty = not value

            if empty and not isinstance(value, deque):
                value = tuple(value)  # checks for isinstance(value, Iterable)

                empty = not value

            if not empty:
                data = self._init()
                data.extendleft(value)
        else:
            data.extendleft(value)

    @wraps(deque.insert, assigned=_WRAPPER_ASSIGNMENTS)
    def insert(self, i: int, x: _T, /) -> None:
        data = self._data

        if data is None:
            data = self._init()

        return data.insert(i, x)

    @wraps(deque.index, assigned=_WRAPPER_ASSIGNMENTS)
    def index(
        self,
        x: _T,
        start: SupportsIndex | DefaultType = DEFAULT,
        stop: SupportsIndex | DefaultType = DEFAULT,
        /,
    ) -> int:
        if (data := self._data) is not None:
            if start is DEFAULT:
                return data.index(x)
            elif stop is DEFAULT:
                return data.index(x, start)
            else:
                return data.index(x, start, stop)
        else:  # checks for type errors
            if stop is not DEFAULT:
                ()[start:stop]
            elif start is not DEFAULT:
                ()[start:]

        msg = "deque.index(x): x not in deque"
        raise ValueError(msg)

    @wraps(deque.count, assigned=_WRAPPER_ASSIGNMENTS)
    def count(self, x: _T, /) -> int:
        if (data := self._data) is not None:
            return data.count(x)

        return 0

    @wraps(deque.rotate, assigned=_WRAPPER_ASSIGNMENTS)
    def rotate(self, n: SupportsIndex = 1, /) -> None:
        if (data := self._data) is not None:
            data.rotate(n)
            return

        if not isinstance(n, int):
            range(n)  # checks for isinstance(n, SupportsIndex)

    @wraps(deque.reverse, assigned=_WRAPPER_ASSIGNMENTS)
    def reverse(self, /) -> None:
        if (data := self._data) is not None:
            data.reverse()

    @wraps(deque.remove, assigned=_WRAPPER_ASSIGNMENTS)
    def remove(self, value: _T, /) -> None:
        if (data := self._data) is not None:
            data.remove(value)
            return

        msg = "deque.remove(x): x not in deque"
        raise ValueError(msg)

    @wraps(deque.pop, assigned=_WRAPPER_ASSIGNMENTS)
    def pop(self, /) -> _T:  # type: ignore[override]
        if (data := self._data) is not None:
            return data.pop()

        msg = "pop from an empty deque"
        raise IndexError(msg)

    @wraps(deque.popleft, assigned=_WRAPPER_ASSIGNMENTS)
    def popleft(self, /) -> _T:
        if (data := self._data) is not None:
            return data.popleft()

        msg = "pop from an empty deque"
        raise IndexError(msg)

    @wraps(deque.clear, assigned=_WRAPPER_ASSIGNMENTS)
    def clear(self, /) -> None:
        if (data := self._data) is not None:
            data.clear()

    @property
    def maxlen(self, /) -> int | None:
        """maximum size of a deque or None if unbounded"""

        return self._maxlen
