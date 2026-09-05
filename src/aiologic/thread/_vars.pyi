#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from typing import Any, Generic, TypeVar

from aiologic.abc import BaseVar, BaseVarToken

from ._handles import ThreadHandle

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
    BaseVarToken[ThreadVar[_T], ThreadHandle, _T],
    Generic[_T],
):
    __slots__ = ()

    def __init_subclass__(cls, /, **kwargs: Any) -> Never: ...

@final
class ThreadVar(BaseVar[ThreadVarToken[_T], ThreadHandle, _T], Generic[_T]):
    __slots__ = ()

    def __init_subclass__(cls, /, **kwargs: Any) -> Never: ...
    def _current_handle(self, /) -> ThreadHandle: ...
    def _create_token(
        self,
        /,
        key: ThreadHandle,
        value: _T,
    ) -> ThreadVarToken[_T]: ...
