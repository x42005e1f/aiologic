#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import sys
import warnings
import weakref

from types import FunctionType, ModuleType
from typing import TYPE_CHECKING

from ._imports import import_from
from ._markers import DEFAULT
from ._modules import resolve_name

if TYPE_CHECKING:
    from ._markers import DefaultType

    if sys.version_info >= (3, 9):  # PEP 585
        from collections.abc import MutableMapping
    else:
        from typing import MutableMapping

if sys.version_info >= (3, 11):  # runtime introspection support
    from typing import get_overloads, overload
else:  # typing-extensions>=4.2.0
    from typing_extensions import get_overloads, overload


def _issubmodule(module_name: str | None, package_name: str, /) -> bool:
    return module_name is not None and (
        module_name == package_name
        or module_name.startswith(f"{package_name}.")
    )


def _export_one(
    package_name: str,
    qualname: str,
    name: str,
    value: object,
    /,
    *,
    visited: set[int] | DefaultType = DEFAULT,
) -> None:
    # There are various algorithms for processing arbitrary objects. We rely on
    # explicit type checking so that we do not have to deal with singletons and
    # other problematic objects that provide a read-only `__module__`
    # attribute.

    if isinstance(value, type):
        # When we encounter a class, we apply the function not only to it, but
        # also recursively to its members. This allows the user to safely
        # reference class functions during pickling.

        # To avoid changing attributes of objects that are not under our
        # control, we explicitly check whether the class belongs to our
        # package. However, keep in mind that this does not eliminate
        # collisions when the same object belongs to different namespaces that
        # we can reach.
        if not _issubmodule(value.__module__, package_name):
            return  # skip foreign ones

        # There may be situations where the class directly or indirectly
        # references itself (this may be part of the interface). Therefore, we
        # have to keep track of the visited IDs in the current stack to avoid
        # infinite recursion.
        if visited is DEFAULT:
            visited = set()
        elif id(value) in visited:
            return  # skip visited ones

        visited.add(id(value))

        try:
            # The function is applied recursively only to those objects that
            # are defined as direct attributes of the class (via `__dict__`).
            # We could obtain a list of all available attributes via `dir()`
            # and rely on MRO to also handle non-public parents, but this would
            # exacerbate the collision problem.

            # copy the namespace so that it works in case of parallel calls
            for attr_name, attr_value in {**vars(value)}.items():
                if attr_name.startswith("_"):
                    continue  # skip non-public ones

                _export_one(
                    package_name,
                    f"{qualname}.{attr_name}",
                    attr_name,
                    attr_value,
                    visited=visited,
                )
        finally:
            visited.remove(id(value))

        value.__name__ = name
        value.__qualname__ = qualname
        value.__module__ = package_name
    elif isinstance(value, FunctionType):
        # To avoid changing attributes of objects that are not under our
        # control, we explicitly check whether the function belongs to our
        # package. However, keep in mind that this does not eliminate
        # collisions when the same object belongs to different namespaces that
        # we can reach.
        if not _issubmodule(value.__module__, package_name):
            return  # skip foreign ones

        # We have to re-register overloads before updating the function's
        # attributes, as the latter are used by `get_overloads()` as keys.
        for value_overload in get_overloads(value):
            value_overload.__name__ = name
            value_overload.__qualname__ = qualname
            value_overload.__module__ = package_name

            # re-register the overload for `package_name` and `qualname`
            overload(value_overload)

        value.__name__ = name
        value.__qualname__ = qualname
        value.__module__ = package_name
    elif isinstance(value, (classmethod, staticmethod)):
        # We cannot reliably check whether the `classmethod`/`staticmethod`
        # instance belongs to the package, so we always assume that it does.

        _export_one(package_name, qualname, name, value.__func__)

        if sys.version_info >= (3, 10):  # inherit the method attributes
            value.__name__ = name
            value.__qualname__ = qualname
            value.__module__ = package_name
    elif isinstance(value, property):
        # We cannot reliably check whether the `property` instance belongs to
        # the package, so we always assume that it does.

        for func in (value.fget, value.fset, value.fdel):
            if func is None:
                continue

            _export_one(package_name, qualname, name, func)

        if sys.version_info >= (3, 13):  # new `__name__` attribute
            value.__name__ = name


def export(
    package_namespace: ModuleType | MutableMapping[str, object],
    /,
) -> None:
    """
    Prepare *package_namespace* for external use.

    Its contents must be structured as follows:

    * Every non-public submodule/subpackage that is part of the implementation
      has a name that starts with the underscore character (``package._util``).
    * Every public submodule/subpackage that is available for direct use has a
      name that does not start with the underscore character (``package.abc``).
    * Every member of a public submodule/subpackage (including the package
      itself) follows the same naming rules.

    The result of applying the function will be to update attributes of all
    public members so that they look as if they were defined directly in the
    package. If a public submodule/subpackage or class is encountered, the
    function is also applied recursively to its members. Additionally, for each
    public submodule/subpackage (including the package itself), a
    human-readable :keyword:`__all__ <import>` is built, which includes the
    names of all public members that are not submodules/subpackages.

    Typically, the usage is as follows: ``export(globals())`` near the end of
    ``__init__.py``. This allows the package to be safely split into
    subpackages and submodules without breaking pickling on incompatible
    implementation changes and while preserving convenient representations
    (which is especially important for exceptions).

    .. caution::

      If the function updates the same object by different names (or in
      different namespaces), the result is undefined, especially when parallel
      calls are made. So avoid providing access to the same object in different
      ways.
    """

    if TYPE_CHECKING:
        # `sphinx.ext.autodoc` does not support the `__module__` hacks. In
        # particular, 'bysource' ordering will not work, nor will some
        # cross-references. So we skip all on type checking (implied by
        # `SPHINX_AUTODOC_RELOAD_MODULES=1`).
        return

    if isinstance(package_namespace, ModuleType):
        package_name = package_namespace.__name__
        package_namespace = vars(package_namespace)
    else:
        package_name = package_namespace["__name__"]

    public_names = []

    # copy the namespace so that it works in case of parallel calls
    for name, value in {**package_namespace}.items():
        if name.startswith("_"):
            continue  # skip non-public ones

        if isinstance(value, ModuleType):
            # When we encounter another public package (we require all modules
            # to be non-public to avoid redundant operations), we apply the
            # function recursively to it. This allows us to avoid manually
            # calling the function for each such package in `__init__.py`.

            if value.__name__.rpartition(".")[0] != package_name:
                continue  # skip indirect ones

            export(value)
        else:
            public_names.append(name)

            _export_one(package_name, name, name, value)

    # sort the list to make it more human-readable
    public_names.sort()
    public_names.sort(key=str.isupper, reverse=True)

    package_namespace.setdefault("__all__", tuple(public_names))


def _register(
    module_namespace: ModuleType | MutableMapping[str, object],
    link_name: str,
    target: str,
    /,
    *,
    deprecated: bool,
) -> None:
    if isinstance(module_namespace, ModuleType):
        module = module_namespace
        module_name = module_namespace.__name__
        module_namespace = vars(module_namespace)
    else:
        module_name = module_namespace["__name__"]
        module = sys.modules.get(module_name)

        # We need the module object for two reasons. First, it allows us to
        # detect cases where `__getattr__()` is overridden via a `ModuleType`
        # subclass. Second, it is used to provide hints via an
        # `AttributeError`. Therefore, we raise a `RuntimeError` if we cannot
        # obtain it in the known way.
        if module is None or vars(module) is not module_namespace:
            msg = "the module object is not in the module cache"
            raise RuntimeError(msg)

    # to avoid conflicts with other implementations
    try:
        registry_name = _register._registry_name
    except AttributeError:
        _register._registry_name = registry_name = (
            f"_{_register.__module__.replace(*'._')}"
            f"_{_register.__name__}_registry"
        )

    try:
        getattr_impl = module.__getattr__
    except AttributeError:
        # Having a strong reference to the module object creates reference
        # cycles via closure, so we use a weak reference instead.
        module_ref = weakref.ref(module)

        registry = {}  # {link_name: (target_path, deprecated)}

        def getattr_impl(name: str) -> object:
            nonlocal module_name

            module = module_ref()

            if module is None:
                msg = "weakly-referenced module object no longer exists"
                raise ReferenceError(msg)

            # We use the current module name in each call to handle cases where
            # it has been renamed (this may be relevant for manually created
            # module objects).
            module_name = getattr(module, "__name__", module_name)

            # One pattern used for dynamic exports is providing objects from
            # modules that may not exist at runtime. Since their non-existence
            # is expected behavior in some environments (similar to optional
            # attributes of the `os` module), we handle this case by raising an
            # `AttributeError` instead of a `ModuleNotFoundError`, but refer to
            # the original exception to explain why the attribute is missing.
            import_exc = None

            try:
                (target_module_name, target_name), deprecated = registry[name]
            except KeyError:
                pass  # unregistered name
            else:
                try:
                    if target_module_name:
                        value = import_from(target_module_name, target_name)
                    else:
                        value = import_from(module, target_name)
                except ModuleNotFoundError as exc:
                    if exc.name != target_module_name:
                        raise  # a side import

                    import_exc = exc
                else:
                    if deprecated:
                        warnings.warn(
                            f"Use {target_module_name}.{target_name} instead",
                            DeprecationWarning,
                            stacklevel=2,
                        )
                    elif not name.startswith("_"):
                        # see the `export()` function
                        if not isinstance(value, ModuleType):
                            _export_one(module_name, name, name, value)
                        elif value.__name__.rpartition(".")[0] == module_name:
                            export(value)

                    # By using `setdefault()` instead of `setattr()` to cache
                    # the value, we ensure that it will not overwrite any other
                    # value that may be set in parallel by the user.
                    return vars(module).setdefault(name, value)

            try:
                msg = f"module {module_name!r} has not attribute {name!r}"
                exc = AttributeError(msg)
                exc.name = name
                exc.obj = module

                try:
                    raise exc from import_exc
                finally:
                    del exc  # break reference cycles
            finally:
                del import_exc  # break reference cycles

        setattr(getattr_impl, registry_name, registry)

        getattr_impl.__name__ = "__getattr__"
        getattr_impl.__qualname__ = "__getattr__"
        getattr_impl.__module__ = module_name

        getattr_impl = module_namespace.setdefault("__getattr__", getattr_impl)

    try:
        registry = getattr(getattr_impl, registry_name)
    except AttributeError:
        msg = "__getattr__() is already defined"
        raise RuntimeError(msg) from None

    if "." in target:
        try:
            target_path = resolve_name(
                target,
                module_name,
            ).rpartition(".")[::2]
        except ValueError:
            target_path = ("", "")

        if not target_path[0]:
            msg = "`target` is beyond the top-level package"
            raise ValueError(msg)
    else:  # to support uncached module objects
        target_path = ("", target)

    record = (target_path, deprecated)

    if registry.setdefault(link_name, record) is not record:
        msg = f"{link_name!r} is already registered"
        raise RuntimeError(msg)


def export_dynamic(
    module_namespace: ModuleType | MutableMapping[str, object],
    link_name: str,
    target: str,
    /,
) -> None:
    """
    Register a dynamic export (symbolic link) in the specified
    *module_namespace*.

    On the first call, the function defines :meth:`~module.__getattr__` in
    *module_namespace*. When attempting to retrieve an undefined attribute from
    the module object by *link_name*, it imports *target* via
    :func:`import_from`, updates its attributes, caches it in the namespace,
    and returns it.

    *target* can be an absolute path (``package.module.attribute``) or a
    relative path (``..attribute``). If it does not contain the dot character,
    the name relative to the module is implied (``name`` is equivalent to
    ``.name``).

    Useful for defining optional package members that are not available in all
    environments.

    Raises:
      RuntimeError:
        if *link_name* cannot be registered.
      ValueError:
        if *target* is beyond the top-level package.
    """

    _register(module_namespace, link_name, target, deprecated=False)


def export_deprecated(
    module_namespace: ModuleType | MutableMapping[str, object],
    link_name: str,
    target: str,
    /,
) -> None:
    """
    Register a deprecated export (symbolic link) in the specified
    *module_namespace*.

    Like :func:`export_dynamic`, but raises :exc:`DeprecationWarning` on the
    first attempt to access the attribute, and never updates attributes of the
    latter.

    Useful for providing a temporary alias by the old name to a renamed object.
    """

    _register(module_namespace, link_name, target, deprecated=True)
