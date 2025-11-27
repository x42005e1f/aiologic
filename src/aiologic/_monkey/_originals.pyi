#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

import sys

from types import ModuleType

if sys.version_info >= (3, 11):  # runtime introspection support
    from typing import overload
else:  # typing-extensions>=4.2.0
    from typing_extensions import overload

def _eventlet_patched(module_name: str, /) -> bool: ...
def _gevent_patched(module_name: str, /) -> bool: ...
def patched(module_name: str, /) -> bool: ...
@overload
def _import_eventlet_original(module_name: str, /) -> ModuleType: ...
@overload
def _import_eventlet_original(module_name: str, name0: str, /) -> object: ...
@overload
def _import_eventlet_original(
    module_name: str,
    name0: str,
    name1: str,
    /,
    *names: str,
) -> tuple[object, ...]: ...
@overload
def _import_gevent_original(module_name: str, /) -> ModuleType: ...
@overload
def _import_gevent_original(module_name: str, name0: str, /) -> object: ...
@overload
def _import_gevent_original(
    module_name: str,
    name0: str,
    name1: str,
    /,
    *names: str,
) -> tuple[object, ...]: ...
@overload
def import_original(module_name: str, /) -> ModuleType: ...
@overload
def import_original(module_name: str, name0: str, /) -> object: ...
@overload
def import_original(
    module_name: str,
    name0: str,
    name1: str,
    /,
    *names: str,
) -> tuple[object, ...]: ...
