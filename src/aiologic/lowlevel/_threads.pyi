#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from threading import Thread, get_ident, local

from ._greenlets import _GreenletLike

def _is_main_thread() -> bool: ...
def _current_python_thread() -> Thread | None: ...
def _current_eventlet_thread() -> Thread | None: ...
def _current_thread_or_main_greenlet() -> Thread | _GreenletLike: ...
def current_thread() -> Thread: ...

current_thread_ident = get_ident

_local = local
