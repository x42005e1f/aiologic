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
        """
        The underlying generator-like object (see :func:`isgeneratorlike`), if
        the wrapped object is one. Otherwise, raises :exc:`AttributeError`.

        Example:
          >>> def generator_function():
          ...     return
          ...     yield  # generator definition
          >>> async def coroutine_function():
          ...     pass
          >>> gen = GeneratorCoroutineWrapper(generator_function())
          >>> gen.gi
          <generator object generator_function at ...>
          >>> gen.close()
          >>> coro = GeneratorCoroutineWrapper(coroutine_function())
          >>> coro.gi
          Traceback (most recent call last):
          AttributeError: the wrapped object is not a generator
          >>> coro.close()
        """

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
        """
        The underlying coroutine-like object (see :func:`iscoroutinelike`), if
        the wrapped object is one. Otherwise, raises :exc:`AttributeError`.

        Example:
          >>> def generator_function():
          ...     return
          ...     yield  # generator definition
          >>> async def coroutine_function():
          ...     pass
          >>> gen = GeneratorCoroutineWrapper(generator_function())
          >>> gen.cr
          Traceback (most recent call last):
          AttributeError: the wrapped object is not a coroutine
          >>> gen.close()
          >>> coro = GeneratorCoroutineWrapper(coroutine_function())
          >>> coro.cr
          <coroutine object coroutine_function at ...>
          >>> coro.close()
        """

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
        """
        An associated code object of the wrapped object.

        This property is provided for compatibility with
        :data:`types.GeneratorType` instances. It is equivalent to one of the
        following:

        * :attr:`gi.gi_code <gi>`
        * :attr:`cr.cr_code <cr>`

        If none is available, raises :exc:`AttributeError`.

        Example:
          >>> def generator_function():
          ...     return
          ...     yield  # generator definition
          >>> async def coroutine_function():
          ...     pass
          >>> gen = GeneratorCoroutineWrapper(generator_function())
          >>> gen.gi_code
          <code object generator_function at ...>
          >>> gen.close()
          >>> coro = GeneratorCoroutineWrapper(coroutine_function())
          >>> coro.gi_code
          <code object coroutine_function at ...>
          >>> coro.close()
        """

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
        """
        An associated code object of the wrapped object.

        This property is provided for compatibility with
        :data:`types.CoroutineType` instances. It is equivalent to one of the
        following:

        * :attr:`cr.cr_code <cr>`
        * :attr:`gi.gi_code <gi>`

        If none is available, raises :exc:`AttributeError`.

        Example:
          >>> def generator_function():
          ...     return
          ...     yield  # generator definition
          >>> async def coroutine_function():
          ...     pass
          >>> gen = GeneratorCoroutineWrapper(generator_function())
          >>> gen.cr_code
          <code object generator_function at ...>
          >>> gen.close()
          >>> coro = GeneratorCoroutineWrapper(coroutine_function())
          >>> coro.cr_code
          <code object coroutine_function at ...>
          >>> coro.close()
        """

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
        """
        An associated frame object of the wrapped object, or :data:`None` (if
        execution has completed).

        This property is provided for compatibility with
        :data:`types.GeneratorType` instances. It is equivalent to one of the
        following:

        * :attr:`gi.gi_frame <gi>`
        * :attr:`cr.cr_frame <cr>`

        If none is available, raises :exc:`AttributeError`.

        Example:
          >>> def generator_function():
          ...     return
          ...     yield  # generator definition
          >>> async def coroutine_function():
          ...     pass
          >>> gen = GeneratorCoroutineWrapper(generator_function())
          >>> gen.gi_frame
          <frame at ...>
          >>> gen.close()
          >>> gen.gi_frame is None
          True
          >>> coro = GeneratorCoroutineWrapper(coroutine_function())
          >>> coro.gi_frame
          <frame at ...>
          >>> coro.close()
          >>> coro.gi_frame is None
          True
        """

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
        """
        An associated frame object of the wrapped object, or :data:`None` (if
        execution has completed).

        This property is provided for compatibility with
        :data:`types.CoroutineType` instances. It is equivalent to one of the
        following:

        * :attr:`cr.cr_frame <cr>`
        * :attr:`gi.gi_frame <gi>`

        If none is available, raises :exc:`AttributeError`.

        Example:
          >>> def generator_function():
          ...     return
          ...     yield  # generator definition
          >>> async def coroutine_function():
          ...     pass
          >>> gen = GeneratorCoroutineWrapper(generator_function())
          >>> gen.cr_frame
          <frame at ...>
          >>> gen.close()
          >>> gen.cr_frame is None
          True
          >>> coro = GeneratorCoroutineWrapper(coroutine_function())
          >>> coro.cr_frame
          <frame at ...>
          >>> coro.close()
          >>> coro.cr_frame is None
          True
        """

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
        """
        A boolean that is :data:`True` if the wrapped object is currently being
        executed by the interpreter (created, not suspended, and not closed),
        :data:`False` otherwise (see :func:`inspect.getgeneratorstate`).

        This property is provided for compatibility with
        :data:`types.GeneratorType` instances. It is equivalent to one of the
        following:

        * :attr:`gi.gi_running <gi>`
        * :attr:`cr.cr_running <cr>`

        If none is available, raises :exc:`AttributeError`.

        Example:
          >>> def generator_function():
          ...     yield from [target.gi_running]
          >>> async def coroutine_function():
          ...     await GeneratorCoroutineWrapper(generator_function())
          >>> gen = GeneratorCoroutineWrapper(generator_function())
          >>> next(target := gen)
          True
          >>> gen.gi_running
          False
          >>> gen.close()
          >>> coro = GeneratorCoroutineWrapper(coroutine_function())
          >>> next(target := coro)
          True
          >>> coro.gi_running
          False
          >>> coro.close()
        """

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
        """
        A boolean that is :data:`True` if the wrapped object is currently being
        executed by the interpreter (created, not suspended, and not closed),
        :data:`False` otherwise (see :func:`inspect.getcoroutinestate`).

        This property is provided for compatibility with
        :data:`types.CoroutineType` instances. It is equivalent to one of the
        following:

        * :attr:`cr.cr_running <cr>`
        * :attr:`gi.gi_running <gi>`

        If none is available, raises :exc:`AttributeError`.

        Example:
          >>> def generator_function():
          ...     yield from [target.cr_running]
          >>> async def coroutine_function():
          ...     await GeneratorCoroutineWrapper(generator_function())
          >>> gen = GeneratorCoroutineWrapper(generator_function())
          >>> next(target := gen)
          True
          >>> gen.cr_running
          False
          >>> gen.close()
          >>> coro = GeneratorCoroutineWrapper(coroutine_function())
          >>> next(target := coro)
          True
          >>> coro.cr_running
          False
          >>> coro.close()
        """

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
        """
        A boolean that is :data:`True` if the wrapped object is currently
        suspended (created, not running, and not closed), :data:`False`
        otherwise (see :func:`inspect.getgeneratorstate`).

        This property is provided for compatibility with
        :data:`types.GeneratorType` instances (Python ≥3.11). It is equivalent
        to one of the following:

        * :attr:`gi.gi_suspended <gi>`
        * :attr:`cr.cr_suspended <cr>`

        If none is available, raises :exc:`AttributeError`.

        Example:
          >>> def generator_function():
          ...     yield from [target.gi_suspended]
          >>> async def coroutine_function():
          ...     await GeneratorCoroutineWrapper(generator_function())
          >>> gen = GeneratorCoroutineWrapper(generator_function())
          >>> next(target := gen)
          False
          >>> gen.gi_suspended
          True
          >>> gen.close()
          >>> coro = GeneratorCoroutineWrapper(coroutine_function())
          >>> next(target := coro)
          False
          >>> coro.gi_suspended
          True
          >>> coro.close()
        """

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
        """
        A boolean that is :data:`True` if the wrapped object is currently
        suspended (created, not running, and not closed), :data:`False`
        otherwise (see :func:`inspect.getcoroutinestate`).

        This property is provided for compatibility with
        :data:`types.CoroutineType` instances (Python ≥3.11). It is equivalent
        to one of the following:

        * :attr:`cr.cr_suspended <cr>`
        * :attr:`gi.gi_suspended <gi>`

        If none is available, raises :exc:`AttributeError`.

        Example:
          >>> def generator_function():
          ...     yield from [target.cr_suspended]
          >>> async def coroutine_function():
          ...     await GeneratorCoroutineWrapper(generator_function())
          >>> gen = GeneratorCoroutineWrapper(generator_function())
          >>> next(target := gen)
          False
          >>> gen.cr_suspended
          True
          >>> gen.close()
          >>> coro = GeneratorCoroutineWrapper(coroutine_function())
          >>> next(target := coro)
          False
          >>> coro.cr_suspended
          True
          >>> coro.close()
        """

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
        """
        An associated iterated object of the wrapped object, or :data:`None`.

        This property is provided for compatibility with
        :data:`types.GeneratorType` instances. It is equivalent to one of the
        following:

        * :attr:`gi.gi_yieldfrom <gi>`
        * :attr:`cr.cr_await <cr>`

        If none is available, raises :exc:`AttributeError`.

        Example:
          >>> def generator_function():
          ...     yield from [target.gi_yieldfrom]
          >>> async def coroutine_function():
          ...     await GeneratorCoroutineWrapper(generator_function())
          >>> gen = GeneratorCoroutineWrapper(generator_function())
          >>> next(target := gen) is None
          True
          >>> gen.gi_yieldfrom
          <list_iterator object at ...>
          >>> gen.close()
          >>> coro = GeneratorCoroutineWrapper(coroutine_function())
          >>> next(target := coro) is None
          True
          >>> coro.gi_yieldfrom
          <aiologic.meta.GeneratorCoroutineWrapper object at ...>
          >>> coro.close()
        """

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
        """
        An associated iterated object of the wrapped object, or :data:`None`.

        This property is provided for compatibility with
        :data:`types.CoroutineType` instances. It is equivalent to one of the
        following:

        * :attr:`cr.cr_await <cr>`
        * :attr:`gi.gi_yieldfrom <gi>`

        If none is available, raises :exc:`AttributeError`.

        Example:
          >>> def generator_function():
          ...     yield from [target.cr_await]
          >>> async def coroutine_function():
          ...     await GeneratorCoroutineWrapper(generator_function())
          >>> gen = GeneratorCoroutineWrapper(generator_function())
          >>> next(target := gen) is None
          True
          >>> gen.cr_await
          <list_iterator object at ...>
          >>> gen.close()
          >>> coro = GeneratorCoroutineWrapper(coroutine_function())
          >>> next(target := coro) is None
          True
          >>> coro.cr_await
          <aiologic.meta.GeneratorCoroutineWrapper object at ...>
          >>> coro.close()
        """

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
        """
        A tuple of ``(filename, line_number, function_name)`` tuples describing
        the traceback where the wrapped object was created, or :data:`None`
        (see :func:`sys.set_coroutine_origin_tracking_depth`).

        This property is provided for consistency with
        :data:`types.CoroutineType` instances. It is equivalent to one of the
        following:

        * :attr:`gi.gi_origin <gi>`
        * :attr:`cr.cr_origin <cr>`

        If none is available, raises :exc:`AttributeError`.

        Example:
          >>> import sys
          >>> def generator_function():
          ...     return
          ...     yield  # generator definition
          >>> async def coroutine_function():
          ...     pass
          >>> gen = GeneratorCoroutineWrapper(generator_function())
          >>> gen.gi_origin
          Traceback (most recent call last):
          AttributeError: the wrapped object has not attribute 'gi_origin'
          >>> gen.close()
          >>> sys.set_coroutine_origin_tracking_depth(0)
          >>> coro = GeneratorCoroutineWrapper(coroutine_function())
          >>> coro.gi_origin is None
          True
          >>> coro.close()
          >>> sys.set_coroutine_origin_tracking_depth(1)
          >>> coro = GeneratorCoroutineWrapper(coroutine_function())
          >>> coro.gi_origin
          ((..., ..., ...),)
          >>> coro.close()
          >>> sys.set_coroutine_origin_tracking_depth(0)
        """

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
        """
        A tuple of ``(filename, line_number, function_name)`` tuples describing
        the traceback where the wrapped object was created, or :data:`None`
        (see :func:`sys.set_coroutine_origin_tracking_depth`).

        This property is provided for compatibility with
        :data:`types.CoroutineType` instances. It is equivalent to one of the
        following:

        * :attr:`cr.cr_origin <cr>`
        * :attr:`gi.gi_origin <gi>`

        If none is available, raises :exc:`AttributeError`.

        Example:
          >>> import sys
          >>> def generator_function():
          ...     return
          ...     yield  # generator definition
          >>> async def coroutine_function():
          ...     pass
          >>> gen = GeneratorCoroutineWrapper(generator_function())
          >>> gen.cr_origin
          Traceback (most recent call last):
          AttributeError: the wrapped object has not attribute 'cr_origin'
          >>> gen.close()
          >>> sys.set_coroutine_origin_tracking_depth(0)
          >>> coro = GeneratorCoroutineWrapper(coroutine_function())
          >>> coro.cr_origin is None
          True
          >>> coro.close()
          >>> sys.set_coroutine_origin_tracking_depth(1)
          >>> coro = GeneratorCoroutineWrapper(coroutine_function())
          >>> coro.cr_origin
          ((..., ..., ...),)
          >>> coro.close()
          >>> sys.set_coroutine_origin_tracking_depth(0)
        """

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
