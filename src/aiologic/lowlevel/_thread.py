#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from . import _monkey

# third-party patchers can break the original objects from the threading
# module, so we need to use the _thread module in the first place

if _monkey._eventlet_patched("_thread"):
    from sys import modules

    modules[__name__] = _monkey._import_eventlet_original("_thread")

    del modules
else:
    __globals = globals()

    if _monkey._gevent_patched("_thread"):
        __module = _monkey._import_gevent_original("_thread")
    else:
        __module = _monkey._import_python_original("_thread")

    for __key, __value in vars(__module).items():
        if __key.startswith("__"):
            continue

        __globals[__key] = __value

        del __value
        del __key

    del __module
    del __globals

del _monkey
