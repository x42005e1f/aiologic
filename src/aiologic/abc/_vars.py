#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys
import weakref

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from aiologic.meta import MISSING

from ._handles import BaseHandle

if TYPE_CHECKING:
    from types import TracebackType
    from typing import ClassVar

    from aiologic.meta import MissingType

    if sys.version_info >= (3, 9):  # PEP 585
        from collections.abc import Callable
    else:
        from typing import Callable

    if sys.version_info >= (3, 11):  # python/cpython#30842
        from typing import Never
    else:  # typing-extensions>=4.1.0
        from typing_extensions import Never

    if sys.version_info >= (3, 11):  # PEP 673
        from typing import Self
    else:  # typing-extensions>=4.0.0
        from typing_extensions import Self

if sys.version_info >= (3, 11):  # python/cpython#31716: introspectable
    from typing import overload
else:  # typing-extensions>=4.2.0
    from typing_extensions import overload

_T = TypeVar("_T")
_HandleT = TypeVar("_HandleT", bound=BaseHandle[Any])
_BaseVarTokenT = TypeVar("_BaseVarTokenT", bound="BaseVarToken[Any, Any, Any]")
_BaseVarT = TypeVar("_BaseVarT", bound="BaseVar[Any, Any, Any]")
_R = TypeVar("_R")


class BaseVarToken(ABC, Generic[_BaseVarT, _HandleT, _T]):
    __slots__ = (
        "__key",
        "__value",
        "__var",
        "_is_first",
        "_is_used",
    )

    def __init__(self, /, var: _BaseVarT, key: _HandleT, value: _T) -> None:
        super().__init__()

        self.__key = key
        self.__value = value
        self.__var = var

        self._is_first = False
        self._is_used = False

    def __reduce__(self, /) -> Never:
        cls = type(self)
        cls_name = cls.__name__

        msg = f"cannot pickle {cls_name!r} object"
        raise TypeError(msg)

    def __copy__(self, /) -> Never:
        cls = type(self)
        cls_name = cls.__name__

        msg = f"cannot copy {cls_name!r} object"
        raise TypeError(msg)

    def __repr__(self, /) -> str:
        cls = type(self)
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        args_repr = f"{self.__var!r}, {self.__key!r}, {self.__value!r}"
        self_repr = f"{cls_repr}({args_repr})"

        if self._is_used:
            state = "used"
        else:
            state = "unused"

        return f"<{self_repr} at {id(self):#x}: {state}>"

    __hash__: ClassVar[None] = None

    def __enter__(self, /) -> Self:
        return self

    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.__var.reset(self)

    @property
    def var(self, /) -> _BaseVarT:
        return self.__var

    @property
    def key(self, /) -> _HandleT:
        return self.__key

    @property
    def value(self, /) -> _T:
        return self.__value


class _BaseVarItem(weakref.ReferenceType):
    __slots__ = (
        "key",
        "value",
    )


class _BaseVarItems(dict):  # ruff: ignore[subclass-builtin]
    __slots__ = ("__weakref__",)


class _BaseVarRemoveByItem:
    __slots__ = ("__items_weakref",)

    def __init__(self, items, /):
        self.__items_weakref = weakref.ref(items)

    def __call__(self, item, /):
        if (items := self.__items_weakref()) is not None:
            try:
                del items[item.key]
            except KeyError:
                pass


class BaseVar(ABC, Generic[_BaseVarTokenT, _HandleT, _T]):
    __slots__ = (
        "__default",
        "__default_factory",
        "__items",
        "__name",
        "__remove_by_item",
    )

    @overload
    def __new__(
        cls,
        /,
        name: str,
        default: _T | MissingType = MISSING,
        *,
        default_factory: MissingType = MISSING,
    ) -> Self: ...
    @overload
    def __new__(
        cls,
        /,
        name: str,
        default: MissingType = MISSING,
        *,
        default_factory: Callable[[], _T],
    ) -> Self: ...
    def __new__(cls, /, name, default=MISSING, *, default_factory=MISSING):
        if default is not MISSING and default_factory is not MISSING:
            msg = "cannot specify both `default` and `default_factory`"
            raise ValueError(msg)

        self = super().__new__(cls)

        self.__default = default
        self.__default_factory = default_factory
        self.__items = _BaseVarItems()
        self.__name = name
        self.__remove_by_item = _BaseVarRemoveByItem(self.__items)

        return self

    def __getnewargs_ex__(self, /) -> tuple[tuple[Any, ...], dict[str, Any]]:
        args = (self.__name,)

        if self.__default_factory is not MISSING:
            kwargs = {"default_factory": self.__default_factory}
        elif self.__default is not MISSING:
            kwargs = {"default": self.__default}
        else:
            kwargs = {}

        return (args, kwargs)

    def __getstate__(self, /) -> None:
        return None

    def __repr__(self, /) -> str:
        cls = type(self)
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        args_repr = f"{self.__name!r}"
        if self.__default_factory is not MISSING:
            args_repr += f", default_factory={self.__default_factory!r}"
        elif self.__default is not MISSING:
            args_repr += f", default={self.__default!r}"
        self_repr = f"{cls_repr}({args_repr})"

        return f"<{self_repr} at {id(self):#x}>"

    @abstractmethod
    def _current_handle(self, /) -> _HandleT:
        raise NotImplementedError

    @abstractmethod
    def _create_token(self, /, key: _HandleT, value: _T) -> _BaseVarTokenT:
        raise NotImplementedError

    @overload
    def get(
        self,
        /,
        default: _T | MissingType = MISSING,
        *,
        default_factory: MissingType = MISSING,
    ) -> _T: ...
    @overload
    def get(
        self,
        /,
        default: _R,
        *,
        default_factory: MissingType = MISSING,
    ) -> _T | _R: ...
    @overload
    def get(
        self,
        /,
        default: MissingType = MISSING,
        *,
        default_factory: Callable[[], _R],
    ) -> _T | _R: ...
    def get(self, /, default=MISSING, *, default_factory=MISSING):
        if default is not MISSING and default_factory is not MISSING:
            msg = "cannot specify both `default` and `default_factory`"
            raise ValueError(msg)

        handle = self._current_handle()

        try:
            value = self.__items[handle].value
        except KeyError:
            value = MISSING

        if value is MISSING:
            if default_factory is not MISSING:
                return default_factory()

            if default is not MISSING:
                return default

            if self.__default_factory is not MISSING:
                return self.__default_factory()

            if self.__default is not MISSING:
                return self.__default

            raise LookupError(self)

        return value

    def set(self, value: _T | MissingType, /) -> _BaseVarTokenT:
        handle = self._current_handle()

        if (item := self.__items.get(handle)) is not None:
            token = self._create_token(handle, item.value)

            item.value = value
        else:
            token = self._create_token(handle, MISSING)
            token._is_first = True

            item = _BaseVarItem(handle.state, self.__remove_by_item)
            item.key = handle
            item.value = value

            self.__items[handle] = item

        return token

    def reset(self, token: _BaseVarTokenT, /) -> _T | MissingType:
        if token.var is not self:
            msg = "the token belongs to another variable"
            raise ValueError(msg)

        handle = self._current_handle()

        if token.key is not handle:
            msg = "the token belongs to another unit"
            raise ValueError(msg)

        if token._is_used:
            msg = "the token has already been used"
            raise ValueError(msg)

        if (item := self.__items.get(handle)) is not None:
            prev_value = item.value

            if token.value is not MISSING or not token._is_first:
                item.value = token.value
            else:
                del self.__items[handle]
        else:
            prev_value = MISSING

            if token.value is not MISSING or not token._is_first:
                item = _BaseVarItem(handle.state, self.__remove_by_item)
                item.key = handle
                item.value = token.value

                self.__items[handle] = item

        token._is_used = True

        return prev_value

    @property
    def name(self, /) -> str:
        return self.__name

    @property
    def default(self, /) -> _T | MissingType:
        return self.__default

    @property
    def default_factory(self, /) -> Callable[[], _T] | MissingType:
        return self.__default_factory
