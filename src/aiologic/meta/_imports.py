#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from importlib import import_module as _import_module_impl
from typing import TYPE_CHECKING

from ._functions import replaces, replaces_when_imported

if TYPE_CHECKING:
    from types import ModuleType
    from typing import Any

if sys.version_info >= (3, 11):
    from typing import overload
else:
    from typing_extensions import overload


if sys.version_info >= (3, 9):
    from ._functions import copies

    @copies(_import_module_impl)
    def import_module(name: str, package: str | None = None) -> ModuleType:
        return _import_module_impl(name, package)

else:
    from importlib.util import resolve_name as _resolve_name_impl

    def import_module(name: str, package: str | None = None) -> ModuleType:
        if name.startswith(".") and package:
            try:
                name = _resolve_name_impl(name, package)
            except ValueError as exc:
                msg = str(exc)
                raise ImportError(msg) from None

        return _import_module_impl(name, package)


def _import_one(module, name, /, *, import_submodule=True):
    try:
        return getattr(module, name)
    except AttributeError:
        pass

    module_name = module.__name__
    module_path = getattr(module, "__file__", None)

    if import_submodule and sys.modules.get(module_name) is module:
        submodule_name = f"{module_name}.{name}"

        try:
            import_module(submodule_name)
        except ModuleNotFoundError as exc:
            if exc.name != submodule_name:
                raise
        else:
            try:
                return getattr(module, name)
            except AttributeError:
                pass

    msg = (
        f"cannot import name {name!r} from {module_name!r}"
        f" ({module_path or 'unknown location'})"
    )
    exc = ImportError(msg)
    exc.name = module_name
    exc.name_from = name
    exc.path = module_path

    try:
        raise exc
    finally:
        del exc


@overload
def import_from(
    module: ModuleType | str,
    name0: str,
    /,
    *,
    package: str | None = None,
) -> Any: ...
@overload
def import_from(
    module: ModuleType | str,
    name0: str,
    name1: str,
    /,
    *names: str,
    package: str | None = None,
) -> tuple[Any, ...]: ...
def import_from(module, name0, /, *names, package=None):
    if isinstance(module, str):
        module = import_module(module, package)

    first = _import_one(module, name0)

    if names:
        return (first, *(_import_one(module, name) for name in names))

    return first


def _import_eventlet_original(module, module_name, name0, /, *names):
    return import_from(module, name0, *names)


@replaces_when_imported(globals(), "eventlet.patcher")
def _import_eventlet_original(module, module_name, name0, /, *names):
    from eventlet.patcher import original

    @replaces(globals())
    def _import_eventlet_original(module, module_name, name0, /, *names):
        return import_from(original(module_name), name0, *names)

    return _import_eventlet_original(module, module_name, name0, *names)


def _import_gevent_original(module, module_name, name0, /, *names):
    return import_from(module, name0, *names)


@replaces_when_imported(globals(), "gevent.monkey")
def _import_gevent_original(module, module_name, name0, /, *names):
    from gevent.monkey import get_original, is_object_patched

    def _import_gevent_one(module, module_name, name, /):
        if is_object_patched(module_name, name):
            return get_original(module_name, name)

        return _import_one(module, name, import_submodule=False)

    @replaces(globals())
    def _import_gevent_original(module, module_name, name0, /, *names):
        first = _import_gevent_one(module, module_name, name0)

        if names:
            return (
                first,
                *(
                    _import_gevent_one(module, module_name, name)
                    for name in names
                ),
            )

        return first

    return _import_gevent_original(module, module_name, name0, *names)


@overload
def import_original(
    module: ModuleType | str,
    name0: str,
    /,
    *,
    package: str | None = None,
) -> Any: ...
@overload
def import_original(
    module: ModuleType | str,
    name0: str,
    name1: str,
    /,
    *names: str,
    package: str | None = None,
) -> tuple[Any, ...]: ...
def import_original(module, name0, /, *names, package=None):
    if isinstance(module, str):
        module = import_module(module, package)

    module_name = module.__name__

    if _iseventletpatched(module_name):
        return _import_eventlet_original(module, module_name, name0, *names)

    if _isgeventpatched(module_name):
        return _import_gevent_original(module, module_name, name0, *names)

    result = import_from(module, name0, *names)

    if _iseventletpatched(module_name):
        return _import_eventlet_original(module, module_name, name0, *names)

    if _isgeventpatched(module_name):
        return _import_gevent_original(module, module_name, name0, *names)

    return result


def _iseventletpatched(module_name, /):
    return False


@replaces_when_imported(globals(), "eventlet.patcher")
def _iseventletpatched(module_name, /):
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
    def _iseventletpatched(module_name, /):
        return mapping.get(module_name, module_name) in already_patched

    return _iseventletpatched(module_name)


def _isgeventpatched(module_name, /):
    return False


@replaces_when_imported(globals(), "gevent.monkey")
def _isgeventpatched(module_name, /):
    global _isgeventpatched

    from gevent.monkey import is_module_patched

    _isgeventpatched = is_module_patched

    return _isgeventpatched(module_name)


def isgreenpatched(module: ModuleType | str, /) -> bool:
    if isinstance(module, str):
        return _isgeventpatched(module) or _iseventletpatched(module)

    module_name = module.__name__

    return module is sys.modules.get(module_name) and (
        _isgeventpatched(module_name) or _iseventletpatched(module_name)
    )
