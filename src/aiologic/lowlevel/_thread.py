#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from . import _patcher

# third-party patchers can break the original objects from the threading
# module, so we need to use the _thread module in the first place

__module = _patcher.import_original("_thread")

if _patcher._eventlet_patched("_thread"):
    from sys import modules

    modules[__name__] = __module

    del modules
else:
    __globals = globals()

    for __key, __value in vars(__module).items():
        if __key.startswith("__"):
            continue

        __globals[__key] = __value

        del __value
        del __key

    del __globals

del __module
del _patcher
