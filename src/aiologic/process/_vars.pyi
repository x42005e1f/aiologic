#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from typing import Any, Generic, TypeVar

from aiologic.abc import BaseVar, BaseVarToken

from ._handles import ProcessHandle

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
