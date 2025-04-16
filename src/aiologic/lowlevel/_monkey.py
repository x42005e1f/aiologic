#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

from importlib import import_module
from types import ModuleType

from wrapt import when_imported


def _eventlet_patched(module_name: str, /) -> bool:
    return False


def _gevent_patched(module_name: str, /) -> bool:
    return False


@when_imported("eventlet.patcher")
def _eventlet_patched_hook(_: ModuleType) -> None:
    global _eventlet_patched

    def _eventlet_patched(module_name: str, /) -> bool:
        global _eventlet_patched

        from eventlet.patcher import already_patched

        mapping = {
            "_thread": "thread",
            "psycopg2": "psycopg",
            "queue": "thread",
            "selectors": "select",
            "ssl": "socket",
            "threading": "thread",
        }

        def _eventlet_patched(module_name: str, /) -> bool:
            return mapping.get(module_name, module_name) in already_patched

        return _eventlet_patched(module_name)


@when_imported("gevent.monkey")
def _gevent_patched_hook(_: ModuleType) -> None:
    global _gevent_patched

    def _gevent_patched(module_name: str, /) -> bool:
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
def _import_eventlet_original_hook(_: ModuleType) -> None:
    global _import_eventlet_original

    def _import_eventlet_original(module_name: str, /) -> ModuleType:
        global _import_eventlet_original

        from eventlet.patcher import original as _import_eventlet_original

        return _import_eventlet_original(module_name)


@when_imported("gevent.monkey")
def _import_gevent_original_hook(_: ModuleType) -> None:
    global _import_gevent_original

    def _import_gevent_original(module_name: str, /) -> ModuleType:
        global _import_gevent_original

        from gevent.monkey import get_original

        def _import_gevent_original(module_name: str, /) -> ModuleType:
            names = dir(import_module(module_name))

            module = ModuleType(module_name)
            vars(module).update(zip(names, get_original(module_name, names)))

            return module

        return _import_gevent_original(module_name)
