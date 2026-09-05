#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from typing import TYPE_CHECKING, Any, Generic, TypeVar

from aiologic.abc import BaseVar, BaseVarToken

from ._getters import current_thread
from ._handles import ThreadHandle

if TYPE_CHECKING:
    if sys.version_info >= (3, 11):
        from typing import Never
    else:
        from typing_extensions import Never

if sys.version_info >= (3, 11):
    from typing import final
else:
    from typing_extensions import final

_T = TypeVar("_T")


@final
class ThreadVarToken(
    BaseVarToken["ThreadVar[_T]", ThreadHandle, _T],
    Generic[_T],
):
    __slots__ = ()

    def __init_subclass__(cls, /, **kwargs: Any) -> Never:
        bcs = __class__
        bcs_name = bcs.__name__

        msg = f"type {bcs_name!r} is not an acceptable base type"
        raise TypeError(msg)


@final
class ThreadVar(BaseVar[ThreadVarToken[_T], ThreadHandle, _T], Generic[_T]):
    __slots__ = ()

    def __init_subclass__(cls, /, **kwargs: Any) -> Never:
        bcs = __class__
        bcs_name = bcs.__name__

        msg = f"type {bcs_name!r} is not an acceptable base type"
        raise TypeError(msg)

    def _current_handle(self, /) -> ThreadHandle:
        return current_thread()

    def _create_token(
        self,
        /,
        key: ThreadHandle,
        value: _T,
    ) -> ThreadVarToken[_T]:
        return ThreadVarToken(self, key, value)
