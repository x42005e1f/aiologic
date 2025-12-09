#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from typing import TYPE_CHECKING, Any, Final

from .meta import DEFAULT, DefaultType

if TYPE_CHECKING:
    from types import TracebackType

    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self

try:
    from sys import _is_gil_enabled
except ImportError:
    __GIL_ENABLED: Final[bool] = True
else:
    __GIL_ENABLED: Final[bool] = _is_gil_enabled()

_USE_DELATTR: Final[bool] = (
    __GIL_ENABLED or sys.version_info >= (3, 14)  # see python/cpython#127266
)


class BusyResourceError(RuntimeError):
    """..."""


class ResourceGuard:
    """..."""

    __slots__ = (
        "__weakref__",
        "_action",
        "_unlocked",
    )

    def __new__(
        cls,
        _: DefaultType = DEFAULT,
        /,
        action: str | DefaultType = DEFAULT,
    ) -> Self:
        """..."""

        if _ is not DEFAULT:
            msg = "the first argument should not have been passed"
            raise ValueError(msg)

        if action is DEFAULT:
            action = "using"

        self = object.__new__(cls)

        self._action = action

        if _USE_DELATTR:
            self._unlocked = True
        else:
            self._unlocked = [None]

        return self

    def __getnewargs__(self, /) -> tuple[Any, ...]:
        """
        Returns arguments that can be used to create new instances with the
        same initial values.

        Used by:

        * The :mod:`pickle` module for pickling.
        * The :mod:`copy` module for copying.

        The current state does not affect the arguments.

        Example:
            >>> orig = ResourceGuard(action='waiting')
            >>> orig.action
            'waiting'
            >>> copy = ResourceGuard(*orig.__getnewargs__())
            >>> copy.action
            'waiting'
        """

        return (DEFAULT, self._action)

    def __getstate__(self, /) -> None:
        """
        Disables the use of internal state for pickling and copying.
        """

        return None

    def __copy__(self, /) -> Self:
        """..."""

        return self.__class__(self._action)

    def __repr__(self, /) -> str:
        """..."""

        cls = self.__class__
        cls_repr = f"{cls.__module__}.{cls.__qualname__}"

        object_repr = f"{cls_repr}({self._action!r})"

        if not self:
            extra = "unlocked"
        else:
            extra = "locked"

        return f"<{object_repr} at {id(self):#x} [{extra}]>"

    def __bool__(self, /) -> bool:
        """
        Returns :data:`True` if the resource guard is used by any task.

        Used by the standard :ref:`truth testing procedure <truth>`.

        Example:
            >>> using = ResourceGuard()
            >>> bool(using)
            False
            >>> with using:  # resource guard is in use
            ...     bool(using)
            True
            >>> bool(using)
            False
        """

        try:
            return not self._unlocked
        except AttributeError:
            return True

    def __enter__(self, /) -> Self:
        """..."""

        try:
            if _USE_DELATTR:
                del self._unlocked
            else:
                self._unlocked.pop()
        except (AttributeError, IndexError):
            msg = f"another task is already {self._action} this resource"
            raise BusyResourceError(msg) from None

        return self

    def __exit__(
        self,
        /,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """..."""

        if _USE_DELATTR:
            self._unlocked = True
        else:
            self._unlocked.append(None)

    @property
    def action(self, /) -> str:
        """
        The action to guard against.
        """

        return self._action
