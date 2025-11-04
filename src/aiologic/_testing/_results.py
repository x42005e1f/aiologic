#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

from concurrent.futures import BrokenExecutor, Future
from typing import (
    TYPE_CHECKING,
    Any,
    Final,
    Generic,
    Literal,
    NoReturn,
    TypeVar,
    final,
)

from aiologic.lowlevel import (
    async_checkpoint,
    create_async_event,
    create_green_event,
    green_checkpoint,
)

from ._exceptions import _CancelledError, _TimeoutError, get_timeout_exc_class

if TYPE_CHECKING:
    import sys

    if sys.version_info >= (3, 9):
        from collections.abc import Generator
    else:
        from typing import Generator

_T = TypeVar("_T")


class Result(Generic[_T]):
    __slots__ = ("_future",)

    def __init__(self, /, future: Future[_T]) -> None:
        self._future = future

    def __repr__(self, /) -> str:
        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        object_repr = f"{cls_repr}(<Future>)"

        if self._future.running():
            extra = "running"
        elif self._future.done():
            if self._future.cancelled():
                extra = "cancelled"
            elif isinstance(self._future.exception(), _CancelledError):
                extra = "cancelled"
            elif isinstance(self._future.exception(), BrokenExecutor):
                extra = "aborted"
            else:
                extra = "finished"
        else:
            extra = "pending"

        return f"<{object_repr} at {id(self):#x} [{extra}]>"

    def __bool__(self, /) -> bool:
        if not self._future.done():
            return False

        if self._future.cancelled():
            return False

        if self._future.exception() is not None:
            return False

        return bool(self._future.result())

    def __await__(self) -> Generator[Any, Any, _T]:
        if not self._future.done():
            event = create_async_event()
            self._future.add_done_callback(lambda _: event.set())

            success = yield from event.__await__()

            if not success:
                raise get_timeout_exc_class(failback=_TimeoutError)
        else:
            yield from async_checkpoint().__await__()

        try:
            return self._future.result()
        except BaseException:
            self = None  # noqa: PLW0642
            raise

    def wait(self, timeout: float | None = None) -> _T:
        if not self._future.done():
            event = create_green_event()
            self._future.add_done_callback(lambda _: event.set())

            success = event.wait(timeout)

            if not success:
                raise get_timeout_exc_class(failback=_TimeoutError)
        else:
            green_checkpoint()

        try:
            return self._future.result()
        except BaseException:
            self = None  # noqa: PLW0642
            raise

    @property
    def future(self, /) -> Future[_T]:
        return self._future


@final
class FalseResult(Result[Literal[False]]):
    __slots__ = ()

    def __new__(cls, /) -> FalseResult:
        return FALSE_RESULT

    def __init__(self, /) -> None:
        future = Future()
        future.set_result(False)

        super().__init__(future)

    def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn:
        bcs = FalseResult
        bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

        msg = f"type '{bcs_repr}' is not an acceptable base type"
        raise TypeError(msg)

    def __reduce__(self, /) -> str:
        return "FALSE_RESULT"

    def __copy__(self, /) -> FalseResult:
        return FALSE_RESULT

    def __repr__(self, /) -> str:
        return f"{self.__class__.__module__}.FALSE_RESULT"

    def __bool__(self, /) -> bool:
        return False

    def __await__(self) -> Generator[Any, Any, Literal[False]]:
        yield from async_checkpoint().__await__()

        return False

    def wait(self, timeout: float | None = None) -> Literal[False]:
        green_checkpoint()

        return False


@final
class TrueResult(Result[Literal[True]]):
    __slots__ = ()

    def __new__(cls, /) -> TrueResult:
        return TRUE_RESULT

    def __init__(self, /) -> None:
        future = Future()
        future.set_result(True)

        super().__init__(future)

    def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn:
        bcs = TrueResult
        bcs_repr = f"{bcs.__module__}.{bcs.__qualname__}"

        msg = f"type '{bcs_repr}' is not an acceptable base type"
        raise TypeError(msg)

    def __reduce__(self, /) -> str:
        return "TRUE_RESULT"

    def __copy__(self, /) -> TrueResult:
        return TRUE_RESULT

    def __repr__(self, /) -> str:
        return f"{self.__class__.__module__}.TRUE_RESULT"

    def __bool__(self, /) -> bool:
        return True

    def __await__(self) -> Generator[Any, Any, Literal[True]]:
        yield from async_checkpoint().__await__()

        return True

    def wait(self, timeout: float | None = None) -> Literal[True]:
        green_checkpoint()

        return True


FALSE_RESULT: Final[FalseResult] = object.__new__(FalseResult)
FALSE_RESULT.__init__()
TRUE_RESULT: Final[TrueResult] = object.__new__(TrueResult)
TRUE_RESULT.__init__()
