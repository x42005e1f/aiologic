#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from typing import Any, ClassVar, Generic, Never, final, overload

if sys.version_info >= (3, 13):  # PEP 696
    from typing import TypeVar
else:  # typing-extensions>=4.12.0
    from typing_extensions import TypeVar

_T = TypeVar("_T")
_AnyT_co = TypeVar("_AnyT_co", covariant=True, default=Any)

@final
class nonmember:
    __slots__ = ("__name",)

    def __init_subclass__(cls, /, **kwargs: Any) -> Never: ...
    def __reduce__(self, /) -> Never: ...
    def __deepcopy__(self, memo: Any, /) -> Never: ...
    def __copy__(self, /) -> Never: ...
    __hash__: ClassVar[None]  # type: ignore[assignment]
    def __set_name__(self, owner: type, name: str, /) -> None: ...
    @overload
    def __get__(
        self,
        instance: None,
        owner: type,
        /,
    ) -> Any: ...
    @overload
    def __get__(
        self,
        instance: _T,
        owner: type[_T] | None = None,
        /,
    ) -> Never: ...
    @property
    def __objclass__(self, /) -> type: ...
    @property
    def __name__(self, /) -> str: ...

@final
class classonly(Generic[_AnyT_co]):
    __slots__ = (
        "__name",
        "__owner",
        "__wrapped",
    )

    @overload
    def __init__(self, wrapped: _AnyT_co, /) -> None: ...
    @overload
    def __init__(self, /) -> None: ...
    def __init_subclass__(cls, /, **kwargs: Any) -> Never: ...
    def __reduce__(self, /) -> Never: ...
    def __deepcopy__(self, memo: Any, /) -> Never: ...
    def __copy__(self, /) -> Never: ...
    def __repr__(self, /) -> str: ...
    __hash__: ClassVar[None]  # type: ignore[assignment]
    def __set_name__(self, owner: type, name: str, /) -> None: ...
    @overload
    def __get__(
        self,
        instance: None,
        owner: type,
        /,
    ) -> _AnyT_co: ...
    @overload
    def __get__(
        self,
        instance: _T,
        owner: type[_T] | None = None,
        /,
    ) -> Never: ...
    @property
    def __objclass__(self, /) -> type: ...
    @property
    def __name__(self, /) -> str: ...
    @property
    def __wrapped__(self, /) -> _AnyT_co: ...
