#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from typing import TYPE_CHECKING, Generic, TypeVar

from ._inspect import iscoroutinelike, isgeneratorlike

if TYPE_CHECKING:
    from types import CodeType, FrameType, TracebackType
    from typing import Final

    if sys.version_info >= (3, 9):  # PEP 585
        from collections.abc import Awaitable
    else:
        from typing import Awaitable

if sys.version_info >= (3, 9):  # PEP 585
    from collections.abc import Coroutine, Generator
else:
    from typing import Coroutine, Generator

if TYPE_CHECKING:
    if sys.version_info >= (3, 11):  # PEP 673
        from typing import Self
    else:  # typing-extensions>=4.0.0
        from typing_extensions import Self

if sys.version_info >= (3, 11):  # runtime introspection support
    from typing import overload
else:  # typing-extensions>=4.2.0
    from typing_extensions import overload

if TYPE_CHECKING:
    _T = TypeVar("_T")

_ReturnT_co = TypeVar("_ReturnT_co", covariant=True)
_SendT_contra = TypeVar("_SendT_contra", contravariant=True)
_YieldT_co = TypeVar("_YieldT_co", covariant=True)

# python/cpython#82711
_ATTRIBUTE_SUGGESTIONS_OFFERED: Final[bool] = sys.version_info >= (3, 10)


class GeneratorCoroutineWrapper(
    Generator[_YieldT_co, _SendT_contra, _ReturnT_co],
    Coroutine[_YieldT_co, _SendT_contra, _ReturnT_co],
    Generic[_YieldT_co, _SendT_contra, _ReturnT_co],
):
    """..."""

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
    ) -> None:
        """..."""

        self.__name__ = getattr(wrapped, "__name__", None)
        self.__qualname__ = getattr(wrapped, "__qualname__", None)
        self.__wrapped = wrapped

    def __await__(self, /) -> Self:
        """..."""

        return self

    def __iter__(self, /) -> Self:
        """..."""

        return self

    def __next__(self, /) -> _YieldT_co:
        """..."""

        return self.__wrapped.send(None)

    def send(self, value: _SendT_contra, /) -> _YieldT_co:
        """..."""

        return self.__wrapped.send(value)

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
    def throw(self, exc_type, exc_value=None, traceback=None, /):
        """..."""

        if exc_value is None:
            return self.__wrapped.throw(exc_type)
        elif traceback is None:
            return self.__wrapped.throw(exc_type, exc_value)
        else:
            return self.__wrapped.throw(exc_type, exc_value, traceback)

    def close(self, /) -> None:
        """..."""

        self.__wrapped.close()

    @property
    def gi(self, /) -> Generator[_YieldT_co, _SendT_contra, _ReturnT_co]:
        """..."""

        try:
            generator = self.__wrapped_gi
        except AttributeError:
            if isgeneratorlike(wrapped := self.__wrapped):
                self.__wrapped_gi = generator = wrapped
            else:
                self.__wrapped_gi = generator = None

        if generator is None:
            msg = "the wrapped object is not a generator"
            exc = AttributeError(msg)
            if _ATTRIBUTE_SUGGESTIONS_OFFERED:
                exc.name = None  # suppress suggestions

            try:
                raise exc
            finally:
                del exc  # break reference cycles

        return generator

    @property
    def cr(self, /) -> Coroutine[_YieldT_co, _SendT_contra, _ReturnT_co]:
        """..."""

        try:
            coroutine = self.__wrapped_cr
        except AttributeError:
            if iscoroutinelike(wrapped := self.__wrapped):
                self.__wrapped_cr = coroutine = wrapped
            else:
                self.__wrapped_cr = coroutine = None

        if coroutine is None:
            msg = "the wrapped object is not a coroutine"
            exc = AttributeError(msg)
            if _ATTRIBUTE_SUGGESTIONS_OFFERED:
                exc.name = None  # suppress suggestions

            try:
                raise exc
            finally:
                del exc  # break reference cycles

        return coroutine

    @property
    def gi_code(self, /) -> CodeType:
        """..."""

        wrapped = self.__wrapped

        try:
            return wrapped.gi_code
        except AttributeError:
            pass

        try:
            return wrapped.cr_code
        except AttributeError:
            pass

        msg = "the wrapped object has not attribute 'gi_code'"
        exc = AttributeError(msg)
        if _ATTRIBUTE_SUGGESTIONS_OFFERED:
            exc.name = None  # suppress suggestions

        try:
            raise exc
        finally:
            del exc  # break reference cycles

    @property
    def cr_code(self, /) -> CodeType:
        """..."""

        wrapped = self.__wrapped

        try:
            return wrapped.cr_code
        except AttributeError:
            pass

        try:
            return wrapped.gi_code
        except AttributeError:
            pass

        msg = "the wrapped object has not attribute 'cr_code'"
        exc = AttributeError(msg)
        if _ATTRIBUTE_SUGGESTIONS_OFFERED:
            exc.name = None  # suppress suggestions

        try:
            raise exc
        finally:
            del exc  # break reference cycles

    @property
    def gi_frame(self, /) -> FrameType | None:
        """..."""

        wrapped = self.__wrapped

        try:
            return wrapped.gi_frame
        except AttributeError:
            pass

        try:
            return wrapped.cr_frame
        except AttributeError:
            pass

        msg = "the wrapped object has not attribute 'gi_frame'"
        exc = AttributeError(msg)
        if _ATTRIBUTE_SUGGESTIONS_OFFERED:
            exc.name = None  # suppress suggestions

        try:
            raise exc
        finally:
            del exc  # break reference cycles

    @property
    def cr_frame(self, /) -> FrameType | None:
        """..."""

        wrapped = self.__wrapped

        try:
            return wrapped.cr_frame
        except AttributeError:
            pass

        try:
            return wrapped.gi_frame
        except AttributeError:
            pass

        msg = "the wrapped object has not attribute 'cr_frame'"
        exc = AttributeError(msg)
        if _ATTRIBUTE_SUGGESTIONS_OFFERED:
            exc.name = None  # suppress suggestions

        try:
            raise exc
        finally:
            del exc  # break reference cycles

    @property
    def gi_running(self, /) -> bool:
        """..."""

        wrapped = self.__wrapped

        try:
            return wrapped.gi_running
        except AttributeError:
            pass

        try:
            return wrapped.cr_running
        except AttributeError:
            pass

        msg = "the wrapped object has not attribute 'gi_running'"
        exc = AttributeError(msg)
        if _ATTRIBUTE_SUGGESTIONS_OFFERED:
            exc.name = None  # suppress suggestions

        try:
            raise exc
        finally:
            del exc  # break reference cycles

    @property
    def cr_running(self, /) -> bool:
        """..."""

        wrapped = self.__wrapped

        try:
            return wrapped.cr_running
        except AttributeError:
            pass

        try:
            return wrapped.gi_running
        except AttributeError:
            pass

        msg = "the wrapped object has not attribute 'cr_running'"
        exc = AttributeError(msg)
        if _ATTRIBUTE_SUGGESTIONS_OFFERED:
            exc.name = None  # suppress suggestions

        try:
            raise exc
        finally:
            del exc  # break reference cycles

    @property
    def gi_suspended(self, /) -> bool:
        """..."""

        wrapped = self.__wrapped

        try:
            return wrapped.gi_suspended
        except AttributeError:
            pass

        try:
            return wrapped.cr_suspended
        except AttributeError:
            pass

        msg = "the wrapped object has not attribute 'gi_suspended'"
        exc = AttributeError(msg)
        if _ATTRIBUTE_SUGGESTIONS_OFFERED:
            exc.name = None  # suppress suggestions

        try:
            raise exc
        finally:
            del exc  # break reference cycles

    @property
    def cr_suspended(self, /) -> bool:
        """..."""

        wrapped = self.__wrapped

        try:
            return wrapped.cr_suspended
        except AttributeError:
            pass

        try:
            return wrapped.gi_suspended
        except AttributeError:
            pass

        msg = "the wrapped object has not attribute 'cr_suspended'"
        exc = AttributeError(msg)
        if _ATTRIBUTE_SUGGESTIONS_OFFERED:
            exc.name = None  # suppress suggestions

        try:
            raise exc
        finally:
            del exc  # break reference cycles

    @property
    def gi_yieldfrom(self, /) -> object | None:
        """..."""

        wrapped = self.__wrapped

        try:
            return wrapped.gi_yieldfrom
        except AttributeError:
            pass

        try:
            return wrapped.cr_await
        except AttributeError:
            pass

        msg = "the wrapped object has not attribute 'gi_yieldfrom'"
        exc = AttributeError(msg)
        if _ATTRIBUTE_SUGGESTIONS_OFFERED:
            exc.name = None  # suppress suggestions

        try:
            raise exc
        finally:
            del exc  # break reference cycles

    @property
    def cr_await(self, /) -> object | None:
        """..."""

        wrapped = self.__wrapped

        try:
            return wrapped.cr_await
        except AttributeError:
            pass

        try:
            return wrapped.gi_yieldfrom
        except AttributeError:
            pass

        msg = "the wrapped object has not attribute 'cr_await'"
        exc = AttributeError(msg)
        if _ATTRIBUTE_SUGGESTIONS_OFFERED:
            exc.name = None  # suppress suggestions

        try:
            raise exc
        finally:
            del exc  # break reference cycles

    @property
    def gi_origin(self, /) -> tuple[tuple[str, int, str], ...] | None:
        """..."""

        wrapped = self.__wrapped

        try:
            return wrapped.gi_origin
        except AttributeError:
            pass

        try:
            return wrapped.cr_origin
        except AttributeError:
            pass

        msg = "the wrapped object has not attribute 'gi_origin'"
        exc = AttributeError(msg)
        if _ATTRIBUTE_SUGGESTIONS_OFFERED:
            exc.name = None  # suppress suggestions

        try:
            raise exc
        finally:
            del exc  # break reference cycles

    @property
    def cr_origin(self, /) -> tuple[tuple[str, int, str], ...] | None:
        """..."""

        wrapped = self.__wrapped

        try:
            return wrapped.cr_origin
        except AttributeError:
            pass

        try:
            return wrapped.gi_origin
        except AttributeError:
            pass

        msg = "the wrapped object has not attribute 'cr_origin'"
        exc = AttributeError(msg)
        if _ATTRIBUTE_SUGGESTIONS_OFFERED:
            exc.name = None  # suppress suggestions

        try:
            raise exc
        finally:
            del exc  # break reference cycles


async def await_for(awaitable: Awaitable[_T], /) -> _T:
    """
    Wait for *awaitable* to complete.

    Useful when you need to schedule waiting for an awaitable primitive via a
    function that only accepts asynchronous functions.
    """

    return await awaitable
