#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from importlib import import_module
from types import SimpleNamespace

from wrapt import when_imported


def _eventlet_patched(module_name):
    return False


@when_imported("eventlet.patcher")
def _eventlet_patched_hook(_):
    global _eventlet_patched

    def _eventlet_patched(module_name):
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

        def _eventlet_patched(module_name):
            if module_name in mapping:
                return mapping[module_name] in already_patched
            else:
                return module_name in already_patched

        return _eventlet_patched(module_name)


def _gevent_patched(module_name):
    return False


@when_imported("gevent.monkey")
def _gevent_patched_hook(_):
    global _gevent_patched

    def _gevent_patched(module_name):
        global _gevent_patched

        from gevent.monkey import is_module_patched

        _gevent_patched = is_module_patched

        return _gevent_patched(module_name)


def _patched(module_name):
    return _eventlet_patched(module_name) or _gevent_patched(module_name)


_import_python_original = import_module
_import_eventlet_original = import_module


@when_imported("eventlet.patcher")
def _import_eventlet_original_hook(_):
    global _import_eventlet_original

    def _import_eventlet_original(module_name):
        global _import_eventlet_original

        from eventlet.patcher import original

        _import_eventlet_original = original

        return _import_eventlet_original(module_name)


_import_gevent_original = import_module


@when_imported("gevent.monkey")
def _import_gevent_original_hook(_):
    global _import_gevent_original

    def _import_gevent_original(module_name):
        global _import_gevent_original

        from gevent.monkey import saved

        def _import_gevent_original(module_name):
            return SimpleNamespace(**{
                **vars(import_module(module_name)),
                **saved.get(module_name, {}),
            })

        return _import_gevent_original(module_name)
