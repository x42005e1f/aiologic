#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from typing import Any, ClassVar, Never, TypeVar, final, overload

_T = TypeVar("_T")

@final
class nonmember:
    __slots__ = ("__name",)

    def __init__(self, /, name: str | None = None) -> None: ...
    def __init_subclass__(cls, /, **kwargs: Any) -> Never: ...
    def __reduce__(self, /) -> Never: ...
    def __deepcopy__(self, memo: Any, /) -> Never: ...
    def __copy__(self, /) -> Never: ...
    def __repr__(self, /) -> str: ...
    __hash__: ClassVar[None] = None  # type: ignore[assignment]
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
    def __set_name__(self, owner: type, name: str, /) -> None: ...
    @property
    def name(self, /) -> str | None: ...
