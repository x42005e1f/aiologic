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

if sys.version_info >= (3, 11):  # python/cpython#31716: introspectable
    from typing import overload
else:  # typing-extensions>=4.2.0
    from typing_extensions import overload


if sys.version_info >= (3, 9):  # python/cpython#14869
    from ._functions import copies

    @copies(_import_module_impl)
    def import_module(name: str, package: str | None = None) -> ModuleType:
        """
        Import a module by *name* (absolute or relative to *package*).

        Like :func:`importlib.import_module`, but raises :exc:`ImportError`
        instead of :exc:`ValueError` on Python <3.9 to achieve consistent
        behavior across all supported versions of Python.

        Example:
          >>> import_module('sys')
          <module 'sys' (built-in)>
          >>> import_module('sys') is import_module('sys')
          True
          >>> import_module('.abc', 'collections').__name__
          'collections.abc'
          >>> import_module('..abc', 'collections').__name__
          Traceback (most recent call last):
          ImportError: attempted relative import beyond top-level package
        """

        return _import_module_impl(name, package)

else:
    from importlib.util import resolve_name as _resolve_name_impl

    def import_module(name: str, package: str | None = None) -> ModuleType:
        """
        Import a module by *name* (absolute or relative to *package*).

        Like :func:`importlib.import_module`, but raises :exc:`ImportError`
        instead of :exc:`ValueError` on Python <3.9 to achieve consistent
        behavior across all supported versions of Python.

        Example:
          >>> import_module('sys')
          <module 'sys' (built-in)>
          >>> import_module('sys') is import_module('sys')
          True
          >>> import_module('.abc', 'collections').__name__
          'collections.abc'
          >>> import_module('..abc', 'collections').__name__
          Traceback (most recent call last):
          ImportError: attempted relative import beyond top-level package
        """

        # Unlike `importlib.util.resolve_name()`, `importlib.import_module()`
        # raises a `TypeError` for a relative name when the package is `None`
        # (or the empty string). We are preserving this behavior to avoid
        # redefining the function on Python ≥3.9.
        if name.startswith(".") and package:
            try:
                name = _resolve_name_impl(name, package)
            except ValueError as exc:
                msg = str(exc)  # copy the error message
                raise ImportError(msg) from None

        return _import_module_impl(name, package)


def _import_one(module, name, /, *, import_submodule=True):
    try:
        return getattr(module, name)
    except AttributeError:
        pass

    module_name = module.__name__
    module_path = getattr(module, "__file__", None)

    # Not all module objects are "real". For example,
    # `eventlet.patcher.original()` returns a module that is an unpatched
    # version of an existing one, but exists separately, and thus imports of
    # submodules have no effect on it.
    if import_submodule and sys.modules.get(module_name) is module:
        submodule_name = f"{module_name}.{name}"

        # to mimic the `from` clause's behavior (see the `import` statement)
        try:
            import_module(submodule_name)
        except ModuleNotFoundError as exc:
            if exc.name != submodule_name:  # a side import
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
        del exc  # break reference cycles


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
    """
    Import objects by given names from the specified *module*.

    If *module* is a string, :func:`import_module(module, package)
    <import_module>` is used to obtain the module object. It is also used to
    attempt to import a submodule if the module does not contain an attribute
    of the same name.

    Raises:
      ImportError:
        if any given name is not in the module.

    Example:
      >>> pi = import_from('math', 'pi')
      >>> pi
      3.141592653589793
      >>> pi, e = import_from('math', 'pi', 'e')
      >>> pi, e
      (3.141592653589793, 2.718281828459045)
      >>> import_from('sys', 'circus')
      Traceback (most recent call last):
      ImportError: cannot import name 'circus' from 'sys' (...)
    """

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
    from eventlet.patcher import (
        original,  # eventlet>=0.9.5
    )

    @replaces(globals())
    def _import_eventlet_original(module, module_name, name0, /, *names):
        return import_from(original(module_name), name0, *names)

    return _import_eventlet_original(module, module_name, name0, *names)


def _import_gevent_original(module, module_name, name0, /, *names):
    return import_from(module, name0, *names)


@replaces_when_imported(globals(), "gevent.monkey")
def _import_gevent_original(module, module_name, name0, /, *names):
    from gevent.monkey import (
        get_original,  # gevent>=1.0.0
        is_object_patched,  # gevent>=1.2.0
    )

    def _import_gevent_one(module, module_name, name, /):
        # `get_original()` raises an `AttributeError` if the module does not
        # contain an attribute with the specified name, so we only use it when
        # we are certain it will succeed.
        if is_object_patched(module_name, name):
            return get_original(module_name, name)

        # `_import_eventlet_original()` cannot import submodules, so to ensure
        # consistent behavior, we should not do so either.
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
    """
    Import unpatched objects by given names from the specified *module*.

    It behaves the same way as :func:`import_from`, except that it attempts to
    import the objects that have been replaced by some green library (e.g., as
    a result of calling :func:`gevent.monkey.patch_all`) instead of the patched
    ones. However, keep in mind that:

    1. Functions that are not built-in access their :attr:`__globals__
       <function.__globals__>` attribute. Therefore, if the returned object was
       defined in the same module where its patched dependencies are located
       (as in the case of gevent), it may not behave as expected. For example,
       :class:`threading.Semaphore` may still use the patched
       :class:`threading.Lock` for its blocking operations.
    2. If the returned object was defined in a fake module (as in the case of
       eventlet), it may still not behave as expected. For example, all started
       threads may be treated as daemonic just because they are not registered
       in the global dictionary of the patched :mod:`threading` module.
    3. Not all original objects may be available, since some are removed rather
       than replaced.

    Because of the above, you should avoid using any objects that depend in any
    way on the module's state. Check the source code to determine which objects
    can be used reliably.

    Unlike :func:`import_from`, it does not import submodules of patched
    modules.
    """

    if isinstance(module, str):
        module = import_module(module, package)

    module_name = module.__name__

    if _iseventletpatched(module_name):
        return _import_eventlet_original(module, module_name, name0, *names)

    if _isgeventpatched(module_name):
        return _import_gevent_original(module, module_name, name0, *names)

    result = import_from(module, name0, *names)

    if _iseventletpatched(module_name):  # a race condition
        return _import_eventlet_original(module, module_name, name0, *names)

    if _isgeventpatched(module_name):  # a race condition
        return _import_gevent_original(module, module_name, name0, *names)

    return result


def _iseventletpatched(module_name, /):
    return False


@replaces_when_imported(globals(), "eventlet.patcher")
def _iseventletpatched(module_name, /):
    from eventlet.patcher import (
        already_patched,  # eventlet>=0.9.5
    )

    # `eventlet` uses the names of the `eventlet.patcher.monkey_patch()`
    # function's keyword arguments as keys in the `already_patched` dictionary,
    # so we have to map the module name to the corresponding keyword argument
    # name.
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

    from gevent.monkey import (
        is_module_patched,  # gevent>=1.2.0
    )

    _isgeventpatched = is_module_patched

    return _isgeventpatched(module_name)


def isgreenpatched(module: ModuleType | str, /) -> bool:
    """
    Return :data:`True` if *module* has been monkey-patched by any of the
    supported green libraries, :data:`False` otherwise.
    """

    if isinstance(module, str):
        return _isgeventpatched(module) or _iseventletpatched(module)

    module_name = module.__name__

    return module is sys.modules.get(module_name) and (
        _isgeventpatched(module_name) or _iseventletpatched(module_name)
    )
