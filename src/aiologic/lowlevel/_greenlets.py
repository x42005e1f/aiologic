#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from typing import TYPE_CHECKING, Any, Protocol

from wrapt import when_imported

if sys.version_info >= (3, 11):
    from typing import overload
else:
    from typing_extensions import overload

if TYPE_CHECKING:
    from contextvars import Context
    from types import FrameType, TracebackType

    if sys.version_info >= (3, 9):
        from collections.abc import Callable
    else:
        from typing import Callable


class _GreenletLike(Protocol):
    def __init__(
        self,
        run: Callable[..., Any] | None = None,
        parent: _GreenletLike | None = None,
    ) -> None: ...
    def switch(self, *args: Any, **kwargs: Any) -> Any: ...
    @overload
    def throw(
        self,
        exc_type: type[BaseException] = ...,
        exc_value: BaseException | object = None,
        traceback: TracebackType | None = None,
        /,
    ) -> Any: ...
    @overload
    def throw(
        self,
        exc_type: BaseException = ...,
        exc_value: None = None,
        traceback: TracebackType | None = None,
        /,
    ) -> Any: ...
    @property
    def dead(self) -> bool: ...
    @property
    def gr_context(self) -> Context | None: ...
    @gr_context.setter
    def gr_context(self, value: Context | None) -> None: ...
    @property
    def gr_frame(self) -> FrameType | None: ...

    parent: Any  # due to python/mypy#9202

    @property
    def run(self) -> Callable[..., Any]: ...
    @run.setter
    def run(self, value: Callable[..., Any]) -> None: ...


def _current_greenlet() -> _GreenletLike:
    global _current_greenlet

    from greenlet import getcurrent as _current_greenlet

    return _current_greenlet()


def _main_greenlet() -> _GreenletLike:
    greenlet = _current_greenlet()

    while greenlet.parent is not None:
        greenlet = greenlet.parent

    return greenlet


def _main_greenlet_if_exists() -> _GreenletLike | None:
    return None


@when_imported("greenlet")
def _(_):
    global _main_greenlet_if_exists

    _main_greenlet_if_exists = _main_greenlet
