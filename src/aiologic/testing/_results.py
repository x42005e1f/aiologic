#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

from concurrent.futures import BrokenExecutor, Future
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from aiologic.lowlevel import create_async_event, create_green_event

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
                extra = "cancelled and notified"
            elif isinstance(self._future.exception(), _CancelledError):
                extra = "cancelled and notified"
            elif isinstance(self._future.exception(), BrokenExecutor):
                extra = "aborted"
            else:
                extra = "finished"
        elif self._future.cancelled():
            extra = "cancelled"
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

        return self._future.result()

    def wait(self, timeout: float | None = None) -> _T:
        if not self._future.done():
            event = create_green_event()
            self._future.add_done_callback(lambda _: event.set())

            success = event.wait(timeout)

            if not success:
                raise get_timeout_exc_class(failback=_TimeoutError)

        return self._future.result()

    @property
    def future(self, /) -> Future[_T]:
        return self._future
