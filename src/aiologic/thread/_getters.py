#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import os

from aiologic.meta import import_original, replaces_with_outcome
from aiologic.process import current_process

from ._handles import ThreadHandle
from ._states import ThreadState

if "_is_forking" not in globals():  # to not redefine on reloads
    _is_forking = False


def _before_fork():
    global _is_forking

    _is_forking = True


def _after_fork_in_parent():
    global _is_forking

    _is_forking = False


def _after_fork_in_child():
    global _is_forking

    _current_thread_at_fork()  # to update the `current_thread().process`

    _is_forking = False


def _register_hooks():
    try:
        register_at_fork = os.register_at_fork
    except AttributeError:
        pass
    else:
        marker = object()

        if globals().setdefault("_is_registered", marker) is marker:  # once
            register_at_fork(  # we use lambdas to support reloads
                before=(lambda: _before_fork()),
                after_in_parent=(lambda: _after_fork_in_parent()),
                after_in_child=(lambda: _after_fork_in_child()),
            )


@replaces_with_outcome(globals())
def _get_thread_local():
    local = import_original("threading", "local")

    globals().setdefault("_thread_local", local())

    def impl():
        global _thread_local  # ruff: ignore[global-variable-not-assigned]
        return _thread_local

    return impl


@replaces_with_outcome(globals())
def _current_thread_ident():
    return import_original("threading", "get_ident")


@replaces_with_outcome(globals())
def _current_thread_state():
    thread_local = _get_thread_local()

    def impl():
        try:
            return thread_local.thread_state
        except AttributeError:
            return vars(thread_local).setdefault("thread_state", ThreadState())

    return impl


@replaces_with_outcome(globals())
def _current_thread():
    _register_hooks()

    thread_local = _get_thread_local()

    def impl():
        try:
            return thread_local.thread_handle
        except AttributeError:
            return vars(thread_local).setdefault(
                "thread_handle",
                ThreadHandle(
                    current_process(),
                    _current_thread_state(),
                    _current_thread_ident(),
                ),
            )

    return impl


def _current_thread_at_fork():
    thread_handle = _current_thread()

    if thread_handle._process is not (process_handle := current_process()):
        thread_handle._process = process_handle

    return thread_handle


def current_thread_ident() -> int:
    return _current_thread_ident()


def current_thread_state() -> ThreadState:
    return _current_thread_state()


def current_thread() -> ThreadHandle:
    if _is_forking:
        return _current_thread_at_fork()
    else:
        return _current_thread()
