#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

from aiologic.meta import import_original, replaces_with_outcome

from ._handles import ThreadHandle
from ._states import ThreadState


@replaces_with_outcome(globals())
def _get_thread_local():
    local = import_original("threading", "local")

    # to not redefine on reloads
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
    thread_local = _get_thread_local()

    def impl():
        try:
            return thread_local.thread_handle
        except AttributeError:
            return vars(thread_local).setdefault(
                "thread_handle",
                ThreadHandle(
                    _current_thread_state(),
                    _current_thread_ident(),
                ),
            )

    return impl


def current_thread_ident() -> int:
    return _current_thread_ident()


def current_thread_state() -> ThreadState:
    return _current_thread_state()


def current_thread() -> ThreadHandle:
    return _current_thread()
