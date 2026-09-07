#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import os
import sys
import warnings
import weakref

from inspect import isclass, isfunction, ismodule
from typing import TYPE_CHECKING

from ._imports import import_from
from ._markers import DEFAULT
from ._modules import resolve_name

if TYPE_CHECKING:
    from types import ModuleType
    from typing import Any, Final

    from ._markers import DefaultType

    if sys.version_info >= (3, 9):
        from collections.abc import MutableMapping
    else:
        from typing import MutableMapping

    if sys.version_info >= (3, 13):
        from typing import TypeIs
    else:
        from typing_extensions import TypeIs

if sys.version_info >= (3, 11):
    from typing import get_overloads, overload
else:
    from typing_extensions import get_overloads, overload

_ATTRIBUTE_SUGGESTIONS_OFFERED: Final[bool] = sys.version_info >= (3, 10)
_SPHINX_AUTODOC_RELOAD_MODULES: Final[bool] = bool(
    os.getenv(
        "SPHINX_AUTODOC_RELOAD_MODULES",
        "",
    )
)


def _isbuiltindescriptor(
    value: object,
    /,
) -> TypeIs[classmethod[Any, Any, Any] | staticmethod[Any, Any]]:
    return isinstance(value, (classmethod, staticmethod))


def _isproperty(value: object, /) -> TypeIs[property]:
    return isinstance(value, property)


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
    if isclass(value):
        if not _issubmodule(value.__module__, package_name):
            return

        if visited is DEFAULT:
            visited = set()
        elif id(value) in visited:
            return

        visited.add(id(value))

        try:
            for attr_name, attr_value in {**vars(value)}.items():
                if attr_name.startswith("_"):
                    continue

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
    elif isfunction(value):
        if not _issubmodule(value.__module__, package_name):
            return

        for value_overload in get_overloads(value):
            value_overload.__name__ = name
            value_overload.__qualname__ = qualname
            value_overload.__module__ = package_name

            overload(value_overload)

        value.__name__ = name
        value.__qualname__ = qualname
        value.__module__ = package_name
    elif _isbuiltindescriptor(value):
        _export_one(package_name, qualname, name, value.__func__)

        if sys.version_info >= (3, 10):
            value.__name__ = name
            value.__qualname__ = qualname
            value.__module__ = package_name
    elif _isproperty(value):
        for func in (value.fget, value.fset, value.fdel):
            if func is None:
                continue

            _export_one(package_name, qualname, name, func)

        if sys.version_info >= (3, 13):
            value.__name__ = name


def export(
    package_namespace: ModuleType | MutableMapping[str, object],
    /,
) -> None:
    if TYPE_CHECKING or _SPHINX_AUTODOC_RELOAD_MODULES:
        return

    if ismodule(package_namespace):
        package_name = package_namespace.__name__
        package_namespace = vars(package_namespace)
    else:
        package_name = package_namespace["__name__"]

    public_names = []

    copied_namespace = {**package_namespace}

    if copied_namespace.get("TYPE_CHECKING") is TYPE_CHECKING:
        del copied_namespace["TYPE_CHECKING"]

    if copied_namespace.get("annotations") is annotations:
        del copied_namespace["annotations"]

    for name, value in copied_namespace.items():
        if name.startswith("_"):
            continue

        if ismodule(value):
            if value.__name__.rpartition(".")[0] != package_name:
                continue

            export(value)
        else:
            public_names.append(name)

            _export_one(package_name, name, name, value)

    public_names.sort()
    public_names.sort(key=str.isupper, reverse=True)

    package_namespace.setdefault("__all__", tuple(public_names))


def _register(
    module_namespace: ModuleType | MutableMapping[str, object],
    link_name: str,
    target: str,
    /,
    *,
    deprecation_message: str | DefaultType | None,
) -> None:
    if ismodule(module_namespace):
        module = module_namespace
        module_name = module_namespace.__name__
        module_namespace = vars(module_namespace)
    else:
        module_name = module_namespace["__name__"]
        module = sys.modules.get(module_name)

        if module is None or vars(module) is not module_namespace:
            msg = "the module object is not in the module cache"
            raise RuntimeError(msg)

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
        module_ref = weakref.ref(module)

        registry = {}

        def getattr_impl(name: str) -> object:
            nonlocal module_name

            module = module_ref()

            if module is None:
                msg = "weakly-referenced module object no longer exists"
                raise ReferenceError(msg)

            module_name = getattr(module, "__name__", module_name)

            import_exc = None

            try:
                (
                    (target_module_name, target_name),
                    deprecation_message,
                ) = registry[name]
            except KeyError:
                pass
            else:
                try:
                    if target_module_name:
                        value = import_from(target_module_name, target_name)
                    else:
                        value = import_from(module, target_name)
                except ModuleNotFoundError as exc:
                    if exc.name != target_module_name:
                        raise

                    import_exc = exc
                else:
                    if deprecation_message is not None:
                        if deprecation_message is DEFAULT:
                            deprecation_message = (
                                f"Use {target_module_name}.{target_name}"
                                f" instead"
                            )

                        warnings.warn(
                            deprecation_message,
                            DeprecationWarning,
                            stacklevel=2,
                        )
                    elif not name.startswith("_"):
                        if not ismodule(value):
                            _export_one(module_name, name, name, value)
                        elif value.__name__.rpartition(".")[0] == module_name:
                            export(value)

                    return vars(module).setdefault(name, value)

            try:
                msg = f"module {module_name!r} has not attribute {name!r}"
                exc = AttributeError(msg)
                if _ATTRIBUTE_SUGGESTIONS_OFFERED:
                    exc.name = name
                    exc.obj = module

                try:
                    raise exc from import_exc
                finally:
                    del exc
            finally:
                del import_exc

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
    else:
        target_path = ("", target)

    record = (target_path, deprecation_message)

    if registry.setdefault(link_name, record) != record:
        msg = f"{link_name!r} is already registered"
        raise RuntimeError(msg)


def export_dynamic(
    module_namespace: ModuleType | MutableMapping[str, object],
    link_name: str,
    target: str,
    /,
) -> None:
    _register(module_namespace, link_name, target, deprecation_message=None)


def export_deprecated(
    module_namespace: ModuleType | MutableMapping[str, object],
    link_name: str,
    target: str,
    /,
    message: str | DefaultType = DEFAULT,
) -> None:
    _register(module_namespace, link_name, target, deprecation_message=message)
