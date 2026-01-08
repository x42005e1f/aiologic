#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from types import CodeType, FrameType, TracebackType
from typing import Final, Generic, TypeVar

if sys.version_info >= (3, 9):  # PEP 585
    from collections.abc import Awaitable, Coroutine, Generator
else:
    from typing import Awaitable, Coroutine, Generator

if sys.version_info >= (3, 11):  # PEP 673
    from typing import Self
else:  # typing-extensions>=4.0.0
    from typing_extensions import Self

if sys.version_info >= (3, 11):  # runtime introspection support
    from typing import overload
else:  # typing-extensions>=4.2.0
    from typing_extensions import overload

_T = TypeVar("_T")
_ReturnT_co = TypeVar("_ReturnT_co", covariant=True)
_SendT_contra = TypeVar("_SendT_contra", contravariant=True)
_YieldT_co = TypeVar("_YieldT_co", covariant=True)

_ATTRIBUTE_SUGGESTIONS_OFFERED: Final[bool]

class GeneratorCoroutineWrapper(
    Generator[_YieldT_co, _SendT_contra, _ReturnT_co],
    Coroutine[_YieldT_co, _SendT_contra, _ReturnT_co],
    Generic[_YieldT_co, _SendT_contra, _ReturnT_co],
):
    __slots__ = (
        "__name__",
        "__qualname__",
        "__weakref__",
        "__wrapped",
        "__wrapped_cr",
        "__wrapped_gi",
    )

    __name__: str
    __qualname__: str

    def __init__(
        self,
        wrapped: (
            Generator[_YieldT_co, _SendT_contra, _ReturnT_co]
            | Coroutine[_YieldT_co, _SendT_contra, _ReturnT_co]
        ),
        /,
    ) -> None: ...
    def __await__(self, /) -> Self: ...
    def __iter__(self, /) -> Self: ...
    def __next__(self, /) -> _YieldT_co: ...
    def send(self, value: _SendT_contra, /) -> _YieldT_co: ...
    @overload
    def throw(
        self,
        exc_type: type[BaseException],
        exc_value: BaseException | object = ...,
        traceback: TracebackType | None = ...,
        /,
    ) -> _YieldT_co: ...
    @overload
    def throw(
        self,
        exc_type: BaseException,
        exc_value: None = None,
        traceback: TracebackType | None = ...,
        /,
    ) -> _YieldT_co: ...
    def close(self, /) -> None: ...
    @property
    def gi(self, /) -> Generator[_YieldT_co, _SendT_contra, _ReturnT_co]: ...
    @property
    def cr(self, /) -> Coroutine[_YieldT_co, _SendT_contra, _ReturnT_co]: ...
    @property
    def gi_code(self, /) -> CodeType: ...
    @property
    def cr_code(self, /) -> CodeType: ...
    @property
    def gi_frame(self, /) -> FrameType | None: ...
    @property
    def cr_frame(self, /) -> FrameType | None: ...
    @property
    def gi_running(self, /) -> bool: ...
    @property
    def cr_running(self, /) -> bool: ...
    @property
    def gi_suspended(self, /) -> bool: ...
    @property
    def cr_suspended(self, /) -> bool: ...
    @property
    def gi_yieldfrom(self, /) -> object | None: ...
    @property
    def cr_await(self, /) -> object | None: ...
    @property
    def gi_origin(self, /) -> tuple[tuple[str, int, str], ...] | None: ...
    @property
    def cr_origin(self, /) -> tuple[tuple[str, int, str], ...] | None: ...

async def await_for(awaitable: Awaitable[_T], /) -> _T: ...
