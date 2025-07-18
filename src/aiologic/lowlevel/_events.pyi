#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from abc import ABC, abstractmethod
from typing import Any, Final, Literal, NoReturn, Protocol, final

if sys.version_info >= (3, 13):
    from warnings import deprecated
else:
    from typing_extensions import deprecated

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if sys.version_info >= (3, 9):
    from collections.abc import Generator
else:
    from typing import Generator

_USE_DELATTR: Final[bool]  # see python/cpython#127266

class Event(Protocol):
    __slots__ = ()

    def __bool__(self, /) -> bool: ...
    def set(self, /) -> bool: ...
    def is_set(self, /) -> bool: ...
    def cancelled(self, /) -> bool: ...
    @property
    def shield(self, /) -> bool: ...
    @shield.setter
    def shield(self, /, value: bool) -> None: ...
    @property
    def force(self, /) -> bool: ...
    @force.setter
    def force(self, /, value: bool) -> None: ...

class GreenEvent(ABC, Event):
    __slots__ = ()

    @deprecated("Use create_green_event() instead")
    def __new__(
        cls,
        /,
        *,
        shield: bool = False,
        force: bool = False,
    ) -> Self: ...
    @abstractmethod
    def wait(self, /, timeout: float | None = None) -> bool: ...
    @abstractmethod
    def __bool__(self, /) -> bool: ...
    @abstractmethod
    def set(self, /) -> bool: ...
    @abstractmethod
    def is_set(self, /) -> bool: ...
    @abstractmethod
    def cancelled(self, /) -> bool: ...
    @property
    @abstractmethod
    def shield(self, /) -> bool: ...
    @shield.setter
    @abstractmethod
    def shield(self, /, value: bool) -> None: ...
    @property
    @abstractmethod
    def force(self, /) -> bool: ...
    @force.setter
    @abstractmethod
    def force(self, /, value: bool) -> None: ...

class AsyncEvent(ABC, Event):
    __slots__ = ()

    @deprecated("Use create_async_event() instead")
    def __new__(
        cls,
        /,
        *,
        shield: bool = False,
        force: bool = False,
    ) -> Self: ...
    @abstractmethod
    def __await__(self, /) -> Generator[Any, Any, bool]: ...
    @abstractmethod
    def __bool__(self, /) -> bool: ...
    @abstractmethod
    def set(self, /) -> bool: ...
    @abstractmethod
    def is_set(self, /) -> bool: ...
    @abstractmethod
    def cancelled(self, /) -> bool: ...
    @property
    @abstractmethod
    def shield(self, /) -> bool: ...
    @shield.setter
    @abstractmethod
    def shield(self, /, value: bool) -> None: ...
    @property
    @abstractmethod
    def force(self, /) -> bool: ...
    @force.setter
    @abstractmethod
    def force(self, /, value: bool) -> None: ...

@final
class SetEvent(GreenEvent, AsyncEvent):
    __slots__ = ()

    def __new__(cls, /) -> SetEvent: ...
    def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn: ...
    def __reduce__(self, /) -> str: ...
    def __repr__(self, /) -> str: ...
    def __bool__(self, /) -> Literal[True]: ...
    def __await__(self, /) -> Generator[Any, Any, Literal[True]]: ...
    def wait(self, /, timeout: float | None = None) -> Literal[True]: ...
    def set(self, /) -> Literal[False]: ...
    def is_set(self, /) -> Literal[True]: ...
    def cancelled(self, /) -> Literal[False]: ...
    @property
    def shield(self, /) -> bool: ...
    @shield.setter
    def shield(self, /, value: bool) -> NoReturn: ...
    @property
    def force(self, /) -> bool: ...
    @force.setter
    def force(self, /, value: bool) -> NoReturn: ...

@final
class DummyEvent(GreenEvent, AsyncEvent):
    __slots__ = ()

    def __new__(cls, /) -> DummyEvent: ...
    def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn: ...
    def __reduce__(self, /) -> str: ...
    def __repr__(self, /) -> str: ...
    def __bool__(self, /) -> Literal[True]: ...
    def __await__(self, /) -> Generator[Any, Any, Literal[True]]: ...
    def wait(self, /, timeout: float | None = None) -> Literal[True]: ...
    def set(self, /) -> Literal[False]: ...
    def is_set(self, /) -> Literal[True]: ...
    def cancelled(self, /) -> Literal[False]: ...
    @property
    def shield(self, /) -> bool: ...
    @shield.setter
    def shield(self, /, value: bool) -> NoReturn: ...
    @property
    def force(self, /) -> bool: ...
    @force.setter
    def force(self, /, value: bool) -> NoReturn: ...

@final
class CancelledEvent(GreenEvent, AsyncEvent):
    __slots__ = ()

    def __new__(cls, /) -> CancelledEvent: ...
    def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn: ...
    def __reduce__(self, /) -> str: ...
    def __repr__(self, /) -> str: ...
    def __bool__(self, /) -> Literal[False]: ...
    def __await__(self, /) -> Generator[Any, Any, Literal[False]]: ...
    def wait(self, /, timeout: float | None = None) -> Literal[False]: ...
    def set(self, /) -> Literal[False]: ...
    def is_set(self, /) -> Literal[False]: ...
    def cancelled(self, /) -> Literal[True]: ...
    @property
    def shield(self, /) -> bool: ...
    @shield.setter
    def shield(self, /, value: bool) -> NoReturn: ...
    @property
    def force(self, /) -> bool: ...
    @force.setter
    def force(self, /, value: bool) -> NoReturn: ...

SET_EVENT: Final[SetEvent]
DUMMY_EVENT: Final[DummyEvent]
CANCELLED_EVENT: Final[CancelledEvent]

class _BaseEvent(ABC, Event):
    __slots__ = (
        "_is_cancelled",
        "_is_pending",
        "_is_set",
        "_is_unset",
        "_waiter",
        "force",
        "shield",
    )

    force: bool
    shield: bool

    def __init__(
        self,
        /,
        shield: bool = False,
        force: bool = False,
    ) -> None: ...
    def __bool__(self, /) -> bool: ...
    def set(self, /) -> bool: ...
    def is_set(self, /) -> bool: ...
    def cancelled(self, /) -> bool: ...

@final
class _GreenEventImpl(_BaseEvent, GreenEvent):
    __slots__ = ()

    def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn: ...
    def __reduce__(self, /) -> NoReturn: ...
    def __repr__(self, /) -> str: ...
    def wait(self, /, timeout: float | None = None) -> bool: ...

@final
class _AsyncEventImpl(_BaseEvent, AsyncEvent):
    __slots__ = ()

    def __init_subclass__(cls, /, **kwargs: Any) -> NoReturn: ...
    def __reduce__(self, /) -> NoReturn: ...
    def __repr__(self, /) -> str: ...
    def __await__(self, /) -> Generator[Any, Any, bool]: ...

def create_green_event(
    *,
    shield: bool = False,
    force: bool = False,
) -> GreenEvent: ...
def create_async_event(
    *,
    shield: bool = False,
    force: bool = False,
) -> AsyncEvent: ...
