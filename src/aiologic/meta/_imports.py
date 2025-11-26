#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys

from importlib import import_module as _import_module_impl
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType

if sys.version_info >= (3, 11):  # runtime introspection support
    from typing import overload
else:  # typing-extensions>=4.2.0
    from typing_extensions import overload


if sys.version_info >= (3, 9):
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


def _import_one(module: ModuleType, name: str, /) -> object:
    try:
        return getattr(module, name)
    except AttributeError:
        pass

    module_name = module.__name__
    module_path = getattr(module, "__file__", "")

    # Not all module objects are "real". For example,
    # `eventlet.patcher.original()` returns a module that is an unpatched
    # version of an existing one, but exists separately, and thus imports of
    # submodules have no effect on it.
    if sys.modules.get(module_name) is module:
        submodule_name = f"{module_name}.{name}"

        # to mimic the `from` clause's behavior (see the `import` statement)
        try:
            import_module(submodule_name)
        except ModuleNotFoundError as exc:
            if exc.name != submodule_name:
                raise  # a side import
        else:
            try:
                return getattr(module, name)
            except AttributeError:
                pass

    msg = (
        f"cannot import name {name!r}"
        f" from {module_name!r}"
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
) -> object: ...
@overload
def import_from(
    module: ModuleType | str,
    name0: str,
    name1: str,
    /,
    *names: str,
    package: str | None = None,
) -> tuple[object, ...]: ...
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
