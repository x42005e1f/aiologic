#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from functools import update_wrapper, wraps
from inspect import (
    CO_ASYNC_GENERATOR,
    CO_COROUTINE,
    CO_GENERATOR,
    CO_ITERABLE_COROUTINE,
    isfunction,
)
from types import CoroutineType, FunctionType, GeneratorType
from typing import TYPE_CHECKING, Any, Generic, TypeVar, get_args, get_origin

from ._helpers import await_for
from ._inspect import (
    _isfunctionlike,
    isasyncgenfactory,
    iscoroutinefactory,
    isgeneratorfactory,
)

if TYPE_CHECKING:
    from typing import Final

    if sys.version_info >= (3, 9):  # PEP 585
        from collections.abc import Awaitable, Callable
    else:
        from typing import Awaitable, Callable

if sys.version_info >= (3, 9):  # PEP 585
    from collections.abc import Coroutine, Generator, Iterator
else:
    from typing import Coroutine, Generator, Iterator

if TYPE_CHECKING:
    if sys.version_info >= (3, 10):  # PEP 612
        from typing import ParamSpec
    else:  # typing-extensions>=3.10.0
        from typing_extensions import ParamSpec

if sys.version_info >= (3, 11):  # runtime introspection support
    from typing import overload
else:  # typing-extensions>=4.2.0
    from typing_extensions import overload

if TYPE_CHECKING:
    _T = TypeVar("_T")
    _CallableT = TypeVar("_CallableT", bound=Callable[..., Any])

_IteratorT = TypeVar("_IteratorT", bound=Iterator[Any])

if TYPE_CHECKING:
    _ReturnT = TypeVar("_ReturnT")
    _SendT = TypeVar("_SendT")
    _YieldT = TypeVar("_YieldT")
    _P = ParamSpec("_P")

# python/cpython#110209
_USE_NATIVE_TYPES: Final[bool] = sys.version_info >= (3, 13)

_generator_origins: tuple[type, ...] = (
    GeneratorType,
    Generator,  # is also the origin of `typing.Generator` (a generic alias)
)
_coroutine_origins: tuple[type, ...] = (
    CoroutineType,
    Coroutine,  # is also the origin of `typing.Coroutine` (a generic alias)
)
_generatortype_names: set[str] = {
    "types.GeneratorType",
    "collections.abc.Generator",
    "typing.Generator",
    "typing_extensions.Generator",
    "GeneratorType",
    "Generator",
}
_coroutinetype_names: set[str] = {
    "types.CoroutineType",
    "collections.abc.Coroutine",
    "typing.Coroutine",
    "typing_extensions.Coroutine",
    "CoroutineType",
    "Coroutine",
}
_generatortype_prefixes: tuple[str, ...] = tuple(
    f"{name}[" for name in _generatortype_names
)
_coroutinetype_prefixes: tuple[str, ...] = tuple(
    f"{name}[" for name in _coroutinetype_names
)


@overload
def _get_generictype_args(
    annotation: str,
    /,
    origins: tuple[type, ...] | type,
    prefixes: tuple[str, ...],
    length: int,
) -> tuple[str, ...]: ...
@overload
def _get_generictype_args(
    annotation: Any,
    /,
    origins: tuple[type, ...] | type,
    prefixes: tuple[str, ...],
    length: int,
) -> tuple[Any, ...]: ...
def _get_generictype_args(annotation, /, origins, prefixes, length):
    if isinstance(annotation, str):
        if annotation.endswith("]"):
            if annotation.startswith(prefixes):
                args_string = annotation.partition("[")[2][:-1]

                if args_string.count("[") == args_string.count("]"):
                    args = args_string.split(",")

                    for i, arg in enumerate(args):
                        while arg.count("[") != arg.count("]"):
                            arg = ",".join(args[i : i + 2])  # noqa: PLW2901
                            args[i : i + 2] = [arg]  # noqa: B909

                    return (
                        *(arg.strip() or "Any" for arg in args),
                        *(["Any"] * length),
                    )[:length]

        return ("Any",) * length

    if isinstance(origin := get_origin(annotation), type):
        if issubclass(origin, origins):
            return (*get_args(annotation), *([Any] * length))[:length]

    return (Any,) * length


@overload
def _get_generatortype_args(annotation: str, /) -> tuple[str, str, str]: ...
@overload
def _get_generatortype_args(annotation: Any, /) -> tuple[Any, Any, Any]: ...
def _get_generatortype_args(annotation, /):
    return _get_generictype_args(
        annotation,
        _generator_origins,
        _generatortype_prefixes,
        3,
    )


@overload
def _get_coroutinetype_args(annotation: str, /) -> tuple[str, str, str]: ...
@overload
def _get_coroutinetype_args(annotation: Any, /) -> tuple[Any, Any, Any]: ...
def _get_coroutinetype_args(annotation, /):
    return _get_generictype_args(
        annotation,
        _coroutine_origins,
        _coroutinetype_prefixes,
        3,
    )


def _update_returntype(
    func: _CallableT,
    /,
    transform: Callable[[Any], Any],
) -> _CallableT:
    annotate = getattr(func, "__annotate__", None)  # PEP 649

    if callable(annotate):

        @wraps(annotate)
        def annotate_wrapper(format):
            annotations = annotate(format)

            if "return" in annotations:
                annotations["return"] = transform(annotations["return"])

            return annotations

        func.__annotate__ = annotate_wrapper
    else:
        annotations = getattr(func, "__annotations__", None)

        if isinstance(annotations, dict):
            if "return" in annotations:
                annotations = annotations.copy()

                annotations["return"] = transform(annotations["return"])

                func.__annotations__ = annotations

    return func


def _copy_with_flags(func: _CallableT, /, flags: int) -> _CallableT:
    copy = FunctionType(
        code=func.__code__.replace(co_flags=flags),
        closure=func.__closure__,
        globals=func.__globals__,
        name=func.__name__,
    )
    copy.__defaults__ = func.__defaults__
    copy.__kwdefaults__ = func.__kwdefaults__  # python/cpython#112640

    return update_wrapper(copy, func)


class _AwaitableWrapper(Generic[_IteratorT]):
    __slots__ = ("__it",)

    def __init__(self, iterator: _IteratorT, /) -> None:
        self.__it = iterator

    def __await__(self) -> _IteratorT:
        return self.__it


@overload
def _generator(
    func: Callable[_P, Generator[_YieldT, _SendT, _ReturnT]],
    /,
) -> Callable[_P, GeneratorType[_YieldT, _SendT, _ReturnT]]: ...
@overload
def _generator(
    func: Callable[_P, Coroutine[_YieldT, _SendT, _ReturnT]],
    /,
) -> Callable[_P, GeneratorType[_YieldT, _SendT, _ReturnT]]: ...
@overload
def _generator(
    func: Callable[_P, Awaitable[_T]],
    /,
) -> Callable[_P, GeneratorType[Any, Any, _T]]: ...
@overload
def _generator(
    func: Callable[_P, object],
    /,
) -> Callable[_P, GeneratorType[Any, Any, Any]]: ...
@overload
def _generator(
    func: object,
    /,
) -> Callable[..., GeneratorType[Any, Any, Any]]: ...
def _generator(func, /):
    if not callable(func):
        msg = "the first argument must be callable"
        raise TypeError(msg)

    if isfunction(func) and not hasattr(func, "__compiled__"):  # non-Nuitka
        flags = func.__code__.co_flags

        if flags & CO_GENERATOR:
            return _copy_with_flags(func, flags & ~CO_ITERABLE_COROUTINE)

        if flags & CO_COROUTINE:
            return _copy_with_flags(func, flags & ~CO_COROUTINE | CO_GENERATOR)

        if flags & CO_ASYNC_GENERATOR:
            msg = (
                "cannot transform an asynchronous generator function into a"
                " generator function"
            )
            raise TypeError(msg)

    if isgeneratorfactory(func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            return (yield from func(*args, **kwargs))

        return wrapper

    if iscoroutinefactory(func):
        if hasattr(_generator, "__compiled__"):  # Nuitka

            @wraps(func)
            def wrapper(*args, **kwargs):
                coro = func(*args, **kwargs)

                if hasattr(coro, "__await__"):
                    return (yield from coro.__await__())

                return (yield from await_for(coro).__await__())

        else:

            @wraps(func)
            @_generator
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)

        return wrapper

    if isasyncgenfactory(func):
        msg = (
            "cannot transform an asynchronous generator factory into a"
            " generator function"
        )
        raise TypeError(msg)

    msg = (
        "cannot transform an unknown object into a generator function. Did you"
        " forget to mark the object?"
    )
    raise TypeError(msg)


@overload
def _coroutine(
    func: Callable[_P, Generator[_YieldT, _SendT, _ReturnT]],
    /,
) -> Callable[_P, CoroutineType[_YieldT, _SendT, _ReturnT]]: ...
@overload
def _coroutine(
    func: Callable[_P, Coroutine[_YieldT, _SendT, _ReturnT]],
    /,
) -> Callable[_P, CoroutineType[_YieldT, _SendT, _ReturnT]]: ...
@overload
def _coroutine(
    func: Callable[_P, Awaitable[_T]],
    /,
) -> Callable[_P, CoroutineType[Any, Any, _T]]: ...
@overload
def _coroutine(
    func: Callable[_P, object],
    /,
) -> Callable[_P, CoroutineType[Any, Any, Any]]: ...
@overload
def _coroutine(
    func: object,
    /,
) -> Callable[..., CoroutineType[Any, Any, Any]]: ...
def _coroutine(func, /):
    if not callable(func):
        msg = "the first argument must be callable"
        raise TypeError(msg)

    if isfunction(func) and not hasattr(func, "__compiled__"):  # non-Nuitka
        flags = func.__code__.co_flags

        if flags & CO_GENERATOR:
            return _copy_with_flags(
                func,
                flags & ~(CO_GENERATOR | CO_ITERABLE_COROUTINE) | CO_COROUTINE,
            )

        if flags & CO_COROUTINE:
            return _copy_with_flags(func, flags)

        if flags & CO_ASYNC_GENERATOR:
            msg = (
                "cannot transform an asynchronous generator function into a"
                " coroutine function"
            )
            raise TypeError(msg)

    if iscoroutinefactory(func):

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        return wrapper

    if isgeneratorfactory(func):
        if hasattr(_coroutine, "__compiled__"):  # Nuitka

            @wraps(func)
            async def wrapper(*args, **kwargs):
                return await _AwaitableWrapper(func(*args, **kwargs))

        else:

            @wraps(func)
            @_coroutine
            def wrapper(*args, **kwargs):
                return (yield from func(*args, **kwargs))

        return wrapper

    if isasyncgenfactory(func):
        msg = (
            "cannot transform an asynchronous generator factory into a"
            " coroutine function"
        )
        raise TypeError(msg)

    msg = (
        "cannot transform an unknown object into a coroutine function. Did you"
        " forget to mark the object?"
    )
    raise TypeError(msg)


@overload
def generator(
    func: Callable[_P, Generator[_YieldT, _SendT, _ReturnT]],
    /,
) -> Callable[_P, GeneratorType[_YieldT, _SendT, _ReturnT]]: ...
@overload
def generator(
    func: Callable[_P, Coroutine[_YieldT, _SendT, _ReturnT]],
    /,
) -> Callable[_P, GeneratorType[_YieldT, _SendT, _ReturnT]]: ...
@overload
def generator(
    func: Callable[_P, Awaitable[_T]],
    /,
) -> Callable[_P, GeneratorType[Any, Any, _T]]: ...
@overload
def generator(
    func: Callable[_P, object],
    /,
) -> Callable[_P, GeneratorType[Any, Any, Any]]: ...
@overload
def generator(
    func: object,
    /,
) -> Callable[..., GeneratorType[Any, Any, Any]]: ...
def generator(func, /):
    """..."""

    genfunc = _generator(func)

    if _isfunctionlike(func):
        flags = func.__code__.co_flags
    else:
        flags = 0

    if flags & CO_GENERATOR or isgeneratorfactory(func):

        def transform(annotation):
            args = _get_generatortype_args(annotation)

            if isinstance(annotation, str):
                return f"GeneratorType[{', '.join(args)}]"

            if _USE_NATIVE_TYPES:
                return GeneratorType[args[0], args[1], args[2]]
            else:
                return Generator[args[0], args[1], args[2]]

    elif flags & CO_COROUTINE:

        def transform(annotation):
            if isinstance(annotation, str):
                return f"GeneratorType[Any, Any, {annotation}]"

            if _USE_NATIVE_TYPES:
                return GeneratorType[Any, Any, annotation]
            else:
                return Generator[Any, Any, annotation]

    else:  # a coroutine factory

        def transform(annotation):
            args = _get_coroutinetype_args(annotation)

            if isinstance(annotation, str):
                return f"GeneratorType[{', '.join(args)}]"

            if _USE_NATIVE_TYPES:
                return GeneratorType[args[0], args[1], args[2]]
            else:
                return Generator[args[0], args[1], args[2]]

    return _update_returntype(genfunc, transform)


@overload
def coroutine(
    func: Callable[_P, Generator[_YieldT, _SendT, _ReturnT]],
    /,
) -> Callable[_P, CoroutineType[_YieldT, _SendT, _ReturnT]]: ...
@overload
def coroutine(
    func: Callable[_P, Coroutine[_YieldT, _SendT, _ReturnT]],
    /,
) -> Callable[_P, CoroutineType[_YieldT, _SendT, _ReturnT]]: ...
@overload
def coroutine(
    func: Callable[_P, Awaitable[_T]],
    /,
) -> Callable[_P, CoroutineType[Any, Any, _T]]: ...
@overload
def coroutine(
    func: Callable[_P, object],
    /,
) -> Callable[_P, CoroutineType[Any, Any, Any]]: ...
@overload
def coroutine(
    func: object,
    /,
) -> Callable[..., CoroutineType[Any, Any, Any]]: ...
def coroutine(func, /):
    """..."""

    corofunc = _coroutine(func)

    if _isfunctionlike(func):
        flags = func.__code__.co_flags
    else:
        flags = 0

    if flags & CO_GENERATOR or isgeneratorfactory(func):

        def transform(annotation):
            return _get_generatortype_args(annotation)[-1]

    elif flags & CO_COROUTINE:

        def transform(annotation):
            return annotation

    else:  # a coroutine factory

        def transform(annotation):
            return _get_coroutinetype_args(annotation)[-1]

    return _update_returntype(corofunc, transform)
