#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from typing import Any, Generic, Never, TypeVar, final

from aiologic.abc import BaseVar, BaseVarToken

from ._handles import ProcessHandle

_T = TypeVar("_T")

@final
class ProcessVarToken(
    BaseVarToken[ProcessVar[_T], ProcessHandle, _T],
    Generic[_T],
):
    __slots__ = ()

    def __init_subclass__(cls, /, **kwargs: Any) -> Never: ...

@final
class ProcessVar(BaseVar[ProcessVarToken[_T], ProcessHandle, _T], Generic[_T]):
    __slots__ = ()

    def __init_subclass__(cls, /, **kwargs: Any) -> Never: ...
    def _current_handle(self, /) -> ProcessHandle: ...
    def _create_token(
        self,
        /,
        key: ProcessHandle,
        value: _T,
    ) -> ProcessVarToken[_T]: ...
