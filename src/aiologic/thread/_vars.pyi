#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Any, ClassVar, Generic, TypeVar

from aiologic.meta import MISSING, MissingType

from ._handles import BaseHandle, ThreadHandle

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

if sys.version_info >= (3, 11):  # python/cpython#30530: introspectable
    from typing import final
else:  # typing-extensions>=4.1.0
    from typing_extensions import final

if sys.version_info >= (3, 11):  # python/cpython#31716: introspectable
    from typing import overload
else:  # typing-extensions>=4.2.0
    from typing_extensions import overload

_T = TypeVar("_T")
_HandleT = TypeVar("_HandleT", bound=BaseHandle[Any])
_BaseVarTokenT = TypeVar("_BaseVarTokenT", bound=BaseVarToken[Any, Any, Any])
_BaseVarT = TypeVar("_BaseVarT", bound=BaseVar[Any, Any, Any])
_R = TypeVar("_R")

class BaseVarToken(ABC, Generic[_BaseVarT, _HandleT, _T]):
    __slots__ = (
        "__key",
        "__value",
        "__var",
        "_is_first",
        "_is_used",
    )

    def __init__(
        self,
        /,
        var: _BaseVarT,
        key: _HandleT,
        value: _T,
    ) -> None: ...
    def __reduce__(self, /) -> Never: ...
    def __copy__(self, /) -> Never: ...
    def __repr__(self, /) -> str: ...
    __hash__: ClassVar[None] = None  # type: ignore[assignment]
    def __enter__(self, /) -> Self: ...
    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...
    @property
    def var(self, /) -> _BaseVarT: ...
    @property
    def key(self, /) -> _HandleT: ...
    @property
    def value(self, /) -> _T: ...

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
    def __getnewargs_ex__(
        self,
        /,
    ) -> tuple[tuple[Any, ...], dict[str, Any]]: ...
    def __getstate__(self, /) -> None: ...
    def __repr__(self, /) -> str: ...
    @abstractmethod
    def _current_handle(self, /) -> _HandleT: ...
    @abstractmethod
    def _create_token(
        self,
        /,
        key: _HandleT,
        value: _T,
    ) -> _BaseVarTokenT: ...
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
    def set(self, value: _T | MissingType, /) -> _BaseVarTokenT: ...
    def reset(self, token: _BaseVarTokenT, /) -> _T | MissingType: ...
    @property
    def name(self, /) -> str: ...
    @property
    def default(self, /) -> _T | MissingType: ...
    @property
    def default_factory(self, /) -> Callable[[], _T] | MissingType: ...

@final
class ThreadVarToken(
    BaseVarToken[ThreadVar[_T], ThreadHandle, _T],
    Generic[_T],
):
    __slots__ = ()

    def __init_subclass__(cls, /, **kwargs: Any) -> Never: ...

@final
class ThreadVar(BaseVar[ThreadVarToken[_T], ThreadHandle, _T], Generic[_T]):
    __slots__ = ()

    def __init_subclass__(cls, /, **kwargs: Any) -> Never: ...
    def _current_handle(self, /) -> ThreadHandle: ...
    def _create_token(
        self,
        /,
        key: ThreadHandle,
        value: _T,
    ) -> ThreadVarToken[_T]: ...
