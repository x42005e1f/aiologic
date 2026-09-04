#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from typing import TYPE_CHECKING, Any, Generic, TypeVar

from aiologic.abc import BaseVar, BaseVarToken

from ._getters import current_process
from ._handles import ProcessHandle

if TYPE_CHECKING:
    if sys.version_info >= (3, 11):  # python/cpython#30842
        from typing import Never
    else:  # typing-extensions>=4.1.0
        from typing_extensions import Never

if sys.version_info >= (3, 11):  # python/cpython#30530: introspectable
    from typing import final
else:  # typing-extensions>=4.1.0
    from typing_extensions import final

_T = TypeVar("_T")


@final
class ProcessVarToken(
    BaseVarToken["ProcessVar[_T]", ProcessHandle, _T],
    Generic[_T],
):
    __slots__ = ()

    def __init_subclass__(cls, /, **kwargs: Any) -> Never:
        bcs = __class__  # an implicit closure reference
        bcs_name = bcs.__name__

        msg = f"type {bcs_name!r} is not an acceptable base type"
        raise TypeError(msg)


@final
class ProcessVar(BaseVar[ProcessVarToken[_T], ProcessHandle, _T], Generic[_T]):
    __slots__ = ()

    def __init_subclass__(cls, /, **kwargs: Any) -> Never:
        bcs = __class__  # an implicit closure reference
        bcs_name = bcs.__name__

        msg = f"type {bcs_name!r} is not an acceptable base type"
        raise TypeError(msg)

    def _current_handle(self, /) -> ProcessHandle:
        return current_process()

    def _create_token(
        self,
        /,
        key: ProcessHandle,
        value: _T,
    ) -> ProcessVarToken[_T]:
        return ProcessVarToken(self, key, value)
