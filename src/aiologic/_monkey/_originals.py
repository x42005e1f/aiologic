#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from types import ModuleType

from wrapt import when_imported

from aiologic.meta import import_from, import_module, replaces

if sys.version_info >= (3, 11):  # runtime introspection support
    from typing import overload
else:  # typing-extensions>=4.2.0
    from typing_extensions import overload


def _eventlet_patched(module_name: str, /) -> bool:
    return False


@when_imported("eventlet.patcher")
def _(_):
    @replaces(globals())
    def _eventlet_patched(module_name, /):
        from eventlet.patcher import already_patched

        mapping = {
            "_thread": "thread",
            "psycopg2": "psycopg",
            "queue": "thread",
            "selectors": "select",
            "ssl": "socket",
            "threading": "thread",
        }

        @replaces(globals())
        def _eventlet_patched(module_name, /):
            return mapping.get(module_name, module_name) in already_patched

        return _eventlet_patched(module_name)


def _gevent_patched(module_name: str, /) -> bool:
    return False


@when_imported("gevent.monkey")
def _(_):
    @replaces(globals())
    def _gevent_patched(module_name, /):
        global _gevent_patched

        from gevent.monkey import is_module_patched as _gevent_patched

        return _gevent_patched(module_name)


def patched(module_name: str, /) -> bool:
    return _gevent_patched(module_name) or _eventlet_patched(module_name)


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
def _import_eventlet_original(module_name, /, *names):
    module = import_module(module_name)

    if names:
        return import_from(module, *names)

    return module


@when_imported("eventlet.patcher")
def _(_):
    @replaces(globals())
    def _import_eventlet_original(module_name, /, *names):
        from eventlet.patcher import original

        @replaces(globals())
        def _import_eventlet_original(module_name, /, *names):
            module = original(module_name)

            if names:
                return import_from(module, *names)

            return module

        return _import_eventlet_original(module_name, *names)


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
def _import_gevent_original(module_name, /, *names):
    module = import_module(module_name)

    if names:
        return import_from(module, *names)

    return module


@when_imported("gevent.monkey")
def _(_):
    @replaces(globals())
    def _import_gevent_original(module_name, /, *names):
        from gevent.monkey import get_original, is_object_patched

        @replaces(globals())
        def _import_gevent_original(module_name, /, *names):
            if names:
                values = tuple(
                    get_original(module_name, name)
                    if is_object_patched(module_name, name)
                    else import_from(module_name, name)
                    for name in names
                )

                if len(values) > 1:
                    return values

                return values[0]

            names = dir(import_module(module_name))

            module = ModuleType(module_name)
            vars(module).update(zip(names, get_original(module_name, names)))

            return module

        return _import_gevent_original(module_name, *names)


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
def import_original(module_name, /, *names):
    if _eventlet_patched(module_name):
        return _import_eventlet_original(module_name, *names)

    if _gevent_patched(module_name):
        return _import_gevent_original(module_name, *names)

    if names:
        result = import_from(module_name, *names)
    else:
        result = import_module(module_name)

    if _eventlet_patched(module_name):
        return _import_eventlet_original(module_name, *names)

    if _gevent_patched(module_name):
        return _import_gevent_original(module_name, *names)

    return result
