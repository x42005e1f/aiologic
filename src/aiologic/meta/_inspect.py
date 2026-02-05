#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys
import warnings

from dataclasses import dataclass, field
from inspect import (
    CO_ASYNC_GENERATOR,
    CO_COROUTINE,
    CO_GENERATOR,
    CO_ITERABLE_COROUTINE,
    isawaitable,
    isclass,
    ismethod,
)
from types import AsyncGeneratorType, CoroutineType, GeneratorType
from typing import TYPE_CHECKING

from ._markers import MISSING
from ._signatures import getsro

if TYPE_CHECKING:
    from typing import Any, TypeVar

    from ._markers import MissingType

if sys.version_info >= (3, 9):  # PEP 585
    from collections.abc import AsyncGenerator, Coroutine, Generator
else:
    from typing import AsyncGenerator, Coroutine, Generator

if TYPE_CHECKING:
    if sys.version_info >= (3, 9):  # PEP 585
        from collections.abc import Awaitable, Callable
    else:
        from typing import Awaitable, Callable

if sys.version_info >= (3, 10):  # python/cpython#22336
    from types import NoneType
else:
    NoneType = type(None)

if TYPE_CHECKING:
    if sys.version_info >= (3, 10):  # PEP 612
        from typing import ParamSpec
    else:  # typing-extensions>=3.10.0
        from typing_extensions import ParamSpec

    if sys.version_info >= (3, 10):  # PEP 647
        from typing import TypeGuard
    else:  # typing-extensions>=3.10.0
        from typing_extensions import TypeGuard

    if sys.version_info >= (3, 13):  # PEP 742
        from typing import TypeIs
    else:  # typing-extensions>=4.10.0
        from typing_extensions import TypeIs

if sys.version_info >= (3, 11):  # runtime introspection support
    from typing import overload
else:  # typing-extensions>=4.2.0
    from typing_extensions import overload

if TYPE_CHECKING:
    _T = TypeVar("_T")
    _CallableT = TypeVar("_CallableT", bound=Callable[..., Any])
    _P = ParamSpec("_P")

# the native type is already registered as a subclass of the abstract class,
# but we still specify it explicitly to speed up the fast path
_generator_types: tuple[type, ...] = (GeneratorType, Generator)
_coroutine_types: tuple[type, ...] = (CoroutineType, Coroutine)
_asyncgen_types: tuple[type, ...] = (AsyncGeneratorType, AsyncGenerator)


def isgeneratorlike(obj: object, /) -> TypeIs[Generator[Any, Any, Any]]:
    """
    Return :data:`True` if the object looks like a :term:`generator iterator`,
    that is, implements :class:`collections.abc.Generator`, and :data:`False`
    otherwise.

    Example:
      >>> from collections.abc import Generator
      >>> class SimpleGenerator(Generator):
      ...     def send(self, value):
      ...         return super().send(value)
      ...     def throw(self, typ, val=None, tb=None):
      ...         return super().throw(typ, val, tb)
      >>> def generator_function():
      ...     return
      ...     yield
      >>> isgeneratorlike(object())
      False
      >>> isgeneratorlike(gen := generator_function())
      True
      >>> isgeneratorlike(SimpleGenerator())
      True
    """

    return isinstance(obj, _generator_types)


def iscoroutinelike(obj: object, /) -> TypeIs[Coroutine[Any, Any, Any]]:
    """
    Return :data:`True` if the object looks like a :term:`coroutine`, that is,
    implements :class:`collections.abc.Coroutine`, and :data:`False` otherwise.

    Example:
      >>> from collections.abc import Coroutine, Generator
      >>> class SimpleCoroutine(Coroutine, Generator):
      ...     def __await__(self):
      ...         return self
      ...     def send(self, value):
      ...         return super().send(value)
      ...     def throw(self, typ, val=None, tb=None):
      ...         return super().throw(typ, val, tb)
      >>> async def coroutine_function():
      ...     pass
      >>> iscoroutinelike(object())
      False
      >>> iscoroutinelike(coro := coroutine_function())
      True
      >>> iscoroutinelike(SimpleCoroutine())
      True
      >>> await coro  # to avoid `RuntimeWarning`

    .. caution::

        Some objects, such as generator-based coroutines (see
        :func:`types.coroutine`), may not have the :meth:`~object.__await__`
        method but still behave like coroutine objects. They are also treated
        as coroutine-like objects. So if you want to get an :term:`iterator`
        for such an object, consider using :func:`await_for(obj).__await__()
        <await_for>`.
    """

    return isinstance(obj, _coroutine_types) or (
        isawaitable(obj) and isgeneratorlike(obj)  # generator-based
    )


def isasyncgenlike(obj: object, /) -> TypeIs[AsyncGenerator[Any, Any]]:
    """
    Return :data:`True` if the object looks like an :term:`asynchronous
    generator iterator`, that is, implements
    :class:`collections.abc.AsyncGenerator`, and :data:`False` otherwise.

    Example:
      >>> from collections.abc import AsyncGenerator
      >>> class SimpleAsyncGenerator(AsyncGenerator):
      ...     async def asend(self, value):
      ...         return await super().send(value)
      ...     async def athrow(self, typ, val=None, tb=None):
      ...         return await super().throw(typ, val, tb)
      >>> async def asyncgen_function():
      ...     return
      ...     yield
      >>> isasyncgenlike(object())
      False
      >>> isasyncgenlike(asyncgen := asyncgen_function())
      True
      >>> isasyncgenlike(SimpleAsyncGenerator())
      True
    """

    return isinstance(obj, _asyncgen_types)


@dataclass
class _MarkerInfo:
    name: str
    value: object | MissingType = MISSING
    default: object = field(default_factory=object)


# to avoid conflicts with other implementations
_prefix: str = f"_{__name__.replace(*'._')}"

_generatorfactory_marker: _MarkerInfo = _MarkerInfo(
    f"{_prefix}_generatorfactory_marker",
)
_coroutinefactory_marker: _MarkerInfo = _MarkerInfo(
    f"{_prefix}_coroutinefactory_marker",
)
_asyncgenfactory_marker: _MarkerInfo = _MarkerInfo(
    f"{_prefix}_asyncgenfactory_marker",
)


def _get_generatorfactory_marker() -> _MarkerInfo:
    return _generatorfactory_marker


def _get_coroutinefactory_marker() -> _MarkerInfo:
    return _coroutinefactory_marker


def _get_asyncgenfactory_marker() -> _MarkerInfo:
    return _asyncgenfactory_marker


def _catch_generatorfactory_marker() -> _MarkerInfo:
    if _generatorfactory_marker.value is MISSING:
        _generatorfactory_marker.value = _generatorfactory_marker.default

    return _generatorfactory_marker


if sys.version_info >= (3, 12):  # python/cpython#99247
    from inspect import markcoroutinefunction

    class _MarkerCatchingError(RuntimeError):
        pass

    class _MarkerCatcher:
        __slots__ = (
            "_name",
            "_value",
        )

        def __setattr__(self, /, name, value):
            if hasattr(self, "_value"):
                msg = "the marker has already been set"
                raise _MarkerCatchingError(msg)

            super().__setattr__("_name", name)
            super().__setattr__("_value", value)

        def __call__(self, /):
            raise NotImplementedError

        @property
        def name(self, /):
            try:
                return self._name
            except AttributeError:
                msg = "the marker has not been set"
                raise _MarkerCatchingError(msg) from None

        @property
        def value(self, /):
            try:
                return self._value
            except AttributeError:
                msg = "the marker has not been set"
                raise _MarkerCatchingError(msg) from None

    def _catch_coroutinefactory_marker() -> _MarkerInfo:
        if _coroutinefactory_marker.value is MISSING:
            try:
                catcher = _MarkerCatcher()

                markcoroutinefunction(catcher)

                _coroutinefactory_marker.name = catcher.name
                _coroutinefactory_marker.value = catcher.value
            except _MarkerCatchingError:
                warnings.warn(
                    (
                        "Unable to obtain the standard marker; manually marked"
                        " functions using standard library tools will not be"
                        " recognized; `markcoroutinefactory()` will also not"
                        " affect `inspect.iscoroutinefunction()`"
                    ),
                    RuntimeWarning,
                    stacklevel=3,
                )
                _coroutinefactory_marker.value = (
                    _coroutinefactory_marker.default
                )

        return _coroutinefactory_marker

    _get_coroutinefactory_marker = _catch_coroutinefactory_marker
else:
    from wrapt import when_imported

    def _catch_coroutinefactory_marker() -> _MarkerInfo:
        if _coroutinefactory_marker.value is MISSING:
            try:
                from asyncio.coroutines import _is_coroutine

                _coroutinefactory_marker.name = "_is_coroutine"
                _coroutinefactory_marker.value = _is_coroutine
            except ImportError:
                warnings.warn(
                    (
                        "Unable to obtain the standard marker; manually marked"
                        " functions using standard library tools will not be"
                        " recognized; `markcoroutinefactory()` will also not"
                        " affect `asyncio.iscoroutinefunction()`"
                    ),
                    RuntimeWarning,
                    stacklevel=3,
                )
                _coroutinefactory_marker.value = (
                    _coroutinefactory_marker.default
                )

        return _coroutinefactory_marker

    @when_imported("asyncio")
    def _(_):
        global _get_coroutinefactory_marker

        _get_coroutinefactory_marker = _catch_coroutinefactory_marker


def _catch_asyncgenfactory_marker() -> _MarkerInfo:
    if _asyncgenfactory_marker.value is MISSING:
        _asyncgenfactory_marker.value = _asyncgenfactory_marker.default

    return _asyncgenfactory_marker


def _unwrap_and_check(
    obj: object,
    /,
    flag: int,
    types: tuple[type, ...] | type,
    markers: list[_MarkerInfo],
) -> bool:
    for current, _, _ in getsro(obj):
        for marker in markers:
            if getattr(current, marker.name, MISSING) is marker.value:
                return True

        if not isclass(current):
            code = getattr(current, "__code__", None)

            if code is None:
                continue

            flags = getattr(code, "co_flags", None)

            if flags is None:
                continue

            return bool(flags & flag)

    if isclass(current):
        return issubclass(current, types)

    return False


@overload
def isgeneratorfactory(
    obj: Callable[..., Generator[Any, Any, Any]],
    /,
) -> bool: ...
@overload
def isgeneratorfactory(
    obj: Callable[_P, Awaitable[_T]],
    /,
) -> TypeGuard[Callable[_P, Generator[Any, Any, _T]]]: ...
@overload
def isgeneratorfactory(
    obj: Callable[_P, object],
    /,
) -> TypeGuard[Callable[_P, Generator[Any, Any, Any]]]: ...
@overload
def isgeneratorfactory(
    obj: object,
    /,
) -> TypeGuard[Callable[..., Generator[Any, Any, Any]]]: ...
def isgeneratorfactory(obj, /):
    """
    Return :data:`True` if the object returns a :term:`generator iterator` when
    called, :data:`False` otherwise.

    The following objects are treated as generator factories by default:

    1. A :term:`generator function <generator>`. This is true for both
       user-defined functions and some compiled functions that look like such
       functions (for example, functions compiled via Cython).
    2. A generator type (a class whose instances look like generator iterators;
       see :func:`isgeneratorlike`).
    3. An object manually marked with :func:`markgeneratorfactory`.

    Example:
      >>> from collections.abc import Generator
      >>> class SimpleGenerator(Generator):
      ...     def send(self, value):
      ...         return super().send(value)
      ...     def throw(self, typ, val=None, tb=None):
      ...         return super().throw(typ, val, tb)
      >>> def generator_function():
      ...     return
      ...     yield
      >>> isgeneratorfactory(lambda: None)
      False
      >>> isgeneratorfactory(generator_function)
      True
      >>> isgeneratorfactory(SimpleGenerator)
      True

    For all others, to determine whether an object is a generator factory, a
    recursive algorithm is used that handles at least the following cases:

    1. If it is a function defined by :class:`functools.partialmethod` for some
       object, the latter is checked.
    2. If it is a partial object (an instance of :func:`functools.partial`),
       the object it wraps (:attr:`functools.partial.func`) is checked.
    3. If it is a bound method, the corresponding object
       (:attr:`method.__func__`) is checked.
    4. If it is a callable object, its :meth:`~object.__call__` method is
       checked.

    Example:
      >>> from functools import partial, partialmethod
      >>> class CustomGeneratorCallable:
      ...     def __call__(self):
      ...         return
      ...         yield
      ...     get = partialmethod(__call__)
      >>> class ComplexGeneratorCallable:
      ...     __call__ = CustomGeneratorCallable()
      >>> isgeneratorfactory(CustomGeneratorCallable())
      True
      >>> isgeneratorfactory(CustomGeneratorCallable().get)
      True
      >>> isgeneratorfactory(CustomGeneratorCallable().__call__)
      True
      >>> isgeneratorfactory(partial(CustomGeneratorCallable()))
      True
      >>> isgeneratorfactory(ComplexGeneratorCallable())
      True
    """

    if (marker := _get_generatorfactory_marker()).value is not MISSING:
        markers = [marker]
    else:
        markers = []

    return _unwrap_and_check(
        obj,
        CO_GENERATOR,
        _generator_types,
        markers,
    )


@overload
def iscoroutinefactory(
    obj: Callable[..., Coroutine[Any, Any, Any]],
    /,
) -> bool: ...
@overload
def iscoroutinefactory(
    obj: Callable[_P, Awaitable[_T]],
    /,
) -> TypeGuard[Callable[_P, Coroutine[Any, Any, _T]]]: ...
@overload
def iscoroutinefactory(
    obj: Callable[_P, object],
    /,
) -> TypeGuard[Callable[_P, Coroutine[Any, Any, Any]]]: ...
@overload
def iscoroutinefactory(
    obj: object,
    /,
) -> TypeGuard[Callable[..., Coroutine[Any, Any, Any]]]: ...
def iscoroutinefactory(obj, /):
    """
    Return :data:`True` if the object returns a :term:`coroutine` when called,
    :data:`False` otherwise.

    The following objects are treated as coroutine factories by default:

    1. A :term:`coroutine function` (a function defined with an :keyword:`async
       def` syntax). This is true for both user-defined functions and some
       compiled functions that look like such functions (for example, functions
       compiled via Cython).
    2. A coroutine type (a class whose instances look like coroutines; see
       :func:`iscoroutinelike`).
    3. A generator-based coroutine function marked with
       :func:`asyncio.coroutine` or the corresponding standard marker (on
       Python <3.12).
    4. An object manually marked with :func:`inspect.markcoroutinefunction` or
       the corresponding standard marker (on Python ≥3.12).
    5. An object manually marked with :func:`markcoroutinefactory`.

    Example:
      >>> from collections.abc import Coroutine, Generator
      >>> class SimpleCoroutine(Coroutine, Generator):
      ...     def __await__(self):
      ...         return self
      ...     def send(self, value):
      ...         return super().send(value)
      ...     def throw(self, typ, val=None, tb=None):
      ...         return super().throw(typ, val, tb)
      >>> async def coroutine_function():
      ...     pass
      >>> iscoroutinefactory(lambda: None)
      False
      >>> iscoroutinefactory(coroutine_function)
      True
      >>> iscoroutinefactory(SimpleCoroutine)
      True

    For all others, to determine whether an object is a coroutine factory, a
    recursive algorithm is used that handles at least the following cases:

    1. If it is a function defined by :class:`functools.partialmethod` for some
       object, the latter is checked.
    2. If it is a partial object (an instance of :func:`functools.partial`),
       the object it wraps (:attr:`functools.partial.func`) is checked.
    3. If it is a bound method, the corresponding object
       (:attr:`method.__func__`) is checked.
    4. If it is a callable object, its :meth:`~object.__call__` method is
       checked.

    Example:
      >>> from functools import partial, partialmethod
      >>> class CustomCoroutineCallable:
      ...     async def __call__(self):
      ...         pass
      ...     get = partialmethod(__call__)
      >>> class ComplexCoroutineCallable:
      ...     __call__ = CustomCoroutineCallable()
      >>> iscoroutinefactory(CustomCoroutineCallable())
      True
      >>> iscoroutinefactory(CustomCoroutineCallable().get)
      True
      >>> iscoroutinefactory(CustomCoroutineCallable().__call__)
      True
      >>> iscoroutinefactory(partial(CustomCoroutineCallable()))
      True
      >>> iscoroutinefactory(ComplexCoroutineCallable())
      True
    """

    if (marker := _get_coroutinefactory_marker()).value is not MISSING:
        markers = [marker]
    else:
        markers = []

    return _unwrap_and_check(
        obj,
        CO_COROUTINE | CO_ITERABLE_COROUTINE,
        _coroutine_types,
        markers,
    )


@overload
def isasyncgenfactory(
    obj: Callable[..., AsyncGenerator[Any, Any]],
    /,
) -> bool: ...
@overload
def isasyncgenfactory(
    obj: Callable[_P, object],
    /,
) -> TypeGuard[Callable[_P, AsyncGenerator[Any, Any]]]: ...
@overload
def isasyncgenfactory(
    obj: object,
    /,
) -> TypeGuard[Callable[..., AsyncGenerator[Any, Any]]]: ...
def isasyncgenfactory(obj, /):
    """
    Return :data:`True` if the object returns an :term:`asynchronous generator
    iterator` when called, :data:`False` otherwise.

    The following objects are treated as asynchronous generator factories by
    default:

    1. An :term:`asynchronous generator function <asynchronous generator>`.
       This is true for both user-defined functions and some compiled functions
       that look like such functions (for example, functions compiled via
       Cython).
    2. An asynchronous generator type (a class whose instances look like
       asynchronous generator iterators; see :func:`isasyncgenlike`).
    3. An object manually marked with :func:`markasyncgenfactory`.

    Example:
      >>> from collections.abc import AsyncGenerator
      >>> class SimpleAsyncGenerator(AsyncGenerator):
      ...     async def asend(self, value):
      ...         return await super().send(value)
      ...     async def athrow(self, typ, val=None, tb=None):
      ...         return await super().throw(typ, val, tb)
      >>> async def asyncgen_function():
      ...     return
      ...     yield
      >>> isasyncgenfactory(lambda: None)
      False
      >>> isasyncgenfactory(asyncgen_function)
      True
      >>> isasyncgenfactory(SimpleAsyncGenerator)
      True

    For all others, to determine whether an object is an asynchronous generator
    factory, a recursive algorithm is used that handles at least the following
    cases:

    1. If it is a function defined by :class:`functools.partialmethod` for some
       object, the latter is checked.
    2. If it is a partial object (an instance of :func:`functools.partial`),
       the object it wraps (:attr:`functools.partial.func`) is checked.
    3. If it is a bound method, the corresponding object
       (:attr:`method.__func__`) is checked.
    4. If it is a callable object, its :meth:`~object.__call__` method is
       checked.

    Example:
      >>> from functools import partial, partialmethod
      >>> class CustomAsyncGeneratorCallable:
      ...     async def __call__(self):
      ...         return
      ...         yield
      ...     get = partialmethod(__call__)
      >>> class ComplexAsyncGeneratorCallable:
      ...     __call__ = CustomAsyncGeneratorCallable()
      >>> isasyncgenfactory(CustomAsyncGeneratorCallable())
      True
      >>> isasyncgenfactory(CustomAsyncGeneratorCallable().get)
      True
      >>> isasyncgenfactory(CustomAsyncGeneratorCallable().__call__)
      True
      >>> isasyncgenfactory(partial(CustomAsyncGeneratorCallable()))
      True
      >>> isasyncgenfactory(ComplexAsyncGeneratorCallable())
      True
    """

    if (marker := _get_asyncgenfactory_marker()).value is not MISSING:
        markers = [marker]
    else:
        markers = []

    return _unwrap_and_check(
        obj,
        CO_ASYNC_GENERATOR,
        _asyncgen_types,
        markers,
    )


def markgeneratorfactory(factory: _CallableT, /) -> _CallableT:
    """..."""

    if not callable(factory):
        msg = "the first argument must be callable"
        raise TypeError(msg)

    obj = factory

    while ismethod(obj):
        obj = obj.__func__

    marker = _catch_generatorfactory_marker()

    setattr(obj, marker.name, marker.value)

    return factory


def markcoroutinefactory(factory: _CallableT, /) -> _CallableT:
    """..."""

    if not callable(factory):
        msg = "the first argument must be callable"
        raise TypeError(msg)

    obj = factory

    while ismethod(obj):
        obj = obj.__func__

    marker = _catch_coroutinefactory_marker()

    setattr(obj, marker.name, marker.value)

    return factory


def markasyncgenfactory(factory: _CallableT, /) -> _CallableT:
    """..."""

    if not callable(factory):
        msg = "the first argument must be callable"
        raise TypeError(msg)

    obj = factory

    while ismethod(obj):
        obj = obj.__func__

    marker = _catch_asyncgenfactory_marker()

    setattr(obj, marker.name, marker.value)

    return factory
