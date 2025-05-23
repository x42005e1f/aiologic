#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

from importlib import import_module
from types import ModuleType

from wrapt import when_imported

from ._utils import _replaces as replaces


def _eventlet_patched(module_name: str, /) -> bool:
    return False


def _gevent_patched(module_name: str, /) -> bool:
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


@when_imported("gevent.monkey")
def _(_):
    @replaces(globals())
    def _gevent_patched(module_name, /):
        global _gevent_patched

        from gevent.monkey import is_module_patched as _gevent_patched

        return _gevent_patched(module_name)


def _patched(module_name: str, /) -> bool:
    return _eventlet_patched(module_name) or _gevent_patched(module_name)


def _import_python_original(module_name: str, /) -> ModuleType:
    return import_module(module_name)


def _import_eventlet_original(module_name: str, /) -> ModuleType:
    return import_module(module_name)


def _import_gevent_original(module_name: str, /) -> ModuleType:
    return import_module(module_name)


@when_imported("eventlet.patcher")
def _(_):
    @replaces(globals())
    def _import_eventlet_original(module_name, /):
        global _import_eventlet_original

        from eventlet.patcher import original as _import_eventlet_original

        return _import_eventlet_original(module_name)


@when_imported("gevent.monkey")
def _(_):
    @replaces(globals())
    def _import_gevent_original(module_name, /):
        from gevent.monkey import get_original

        @replaces(globals())
        def _import_gevent_original(module_name, /):
            names = dir(import_module(module_name))

            module = ModuleType(module_name)
            vars(module).update(zip(names, get_original(module_name, names)))

            return module

        return _import_gevent_original(module_name)
