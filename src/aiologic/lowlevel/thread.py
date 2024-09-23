#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

__all__ = ()

from .markers import MISSING
from .patcher import import_original

error = RuntimeError

# third-party patchers can break the original objects from the threading
# module, so we need to use the _thread module in the first place


def start_new_thread(callable, args, kwargs=MISSING):  # PyPy signature
    global start_new_thread

    try:
        start_new_thread = import_original("_thread:start_new_thread")
    except ImportError:
        try:
            start_new_thread = import_original("threading:_start_new_thread")
        except ImportError:
            from builtins import callable as builtins_callable
            from itertools import count

            Thread = import_original("threading:Thread")

            counter = count(1).__next__

            def start_new_thread(callable, args, kwargs=MISSING):
                if not builtins_callable(callable):
                    raise TypeError("first arg must be callable")

                if not isinstance(args, tuple):
                    raise TypeError("2nd arg must be a tuple")

                if kwargs is not MISSING and not isinstance(kwargs, dict):
                    raise TypeError("optional 3rd arg must be a dictionary")

                try:
                    callable_name = callable.__name__
                except AttributeError:
                    name = f"_Thread-{counter()}"
                else:
                    name = f"_Thread-{counter()} ({callable_name})"

                if kwargs is not MISSING:
                    thread = Thread(
                        target=callable,
                        name=name,
                        args=args,
                        kwargs=kwargs,
                        daemon=True,
                    )
                else:
                    thread = Thread(
                        target=callable,
                        name=name,
                        args=args,
                        daemon=True,
                    )

                thread.start()

                return thread.ident

    if kwargs is not MISSING:
        ident = start_new_thread(callable, args, kwargs)
    else:
        ident = start_new_thread(callable, args)

    return ident


try:
    try:
        LockType = import_original("_thread:LockType")
    except ImportError:
        try:
            LockType = import_original("threading:_LockType")
        except ImportError:
            LockType = import_original("threading:Lock")
except ImportError:
    pass
else:
    try:
        allocate_lock = import_original("_thread:allocate_lock")
    except ImportError:
        try:
            allocate_lock = import_original("threading:_allocate_lock")
        except ImportError:
            allocate_lock = import_original("threading:Lock")

try:
    try:
        get_ident = import_original("_thread:get_ident")
    except ImportError:
        get_ident = import_original("threading:get_ident")
except ImportError:
    pass


def __getattr__(name, /):
    if not name.startswith("__") or not name.endswith("__"):
        for template in ("_thread:{}", "threading:_{}", "threading:{}"):
            try:
                value = import_original(template.format(name))
            except ImportError:
                pass
            else:
                if name.isupper() or getattr(value, "__module__", "") == (
                    "_thread"
                ):
                    return globals().setdefault(name, value)

    raise AttributeError(f"module '_thread' has no attribute {name!r}")
