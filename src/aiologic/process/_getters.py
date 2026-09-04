#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

import os

from aiologic.meta import replaces_with_outcome

from ._handles import ProcessHandle
from ._states import ProcessState

if "_is_forking" not in globals():  # to not redefine on reloads
    _is_forking = False


def _before_fork():
    global _is_forking

    _current_process_ident()  # to ensure the parent's `_process_ident`

    _is_forking = True


def _after_fork_in_parent():
    global _is_forking

    _is_forking = False


def _after_fork_in_child():
    global _is_forking

    global _child_handle
    global _child_state
    global _child_ident

    global _process_handle
    global _process_state
    global _process_ident

    _process_handle = _current_child()
    _process_state = _current_child_state()
    _process_ident = _current_child_ident()

    del _child_handle
    del _child_state
    del _child_ident

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
def _current_process_ident():
    _register_hooks()

    globals().setdefault("_process_ident", os.getpid())

    def impl():
        global _process_ident  # ruff: ignore[global-variable-not-assigned]
        return _process_ident

    return impl


@replaces_with_outcome(globals())
def _current_process_state():
    _register_hooks()

    globals().setdefault("_process_state", ProcessState())

    def impl():
        global _process_state  # ruff: ignore[global-variable-not-assigned]
        return _process_state

    return impl


@replaces_with_outcome(globals())
def _current_process():
    _register_hooks()

    globals().setdefault(
        "_process_handle",
        ProcessHandle(
            _current_process_state(),
            _current_process_ident(),
        ),
    )

    def impl():
        global _process_handle  # ruff: ignore[global-variable-not-assigned]
        return _process_handle

    return impl


def _current_child_ident():
    global _child_ident  # ruff: ignore[global-variable-not-assigned]

    if "_child_ident" not in globals():
        globals().setdefault("_child_ident", os.getpid())

    return _child_ident


def _current_child_state():
    global _child_state  # ruff: ignore[global-variable-not-assigned]

    if "_child_state" not in globals():
        globals().setdefault("_child_state", ProcessState())

    return _child_state


def _current_child():
    global _child_handle  # ruff: ignore[global-variable-not-assigned]

    if "_child_handle" not in globals():
        globals().setdefault(
            "_child_handle",
            ProcessHandle(
                _current_child_state(),
                _current_child_ident(),
            ),
        )

    return _child_handle


def current_process_ident() -> int:
    if _is_forking and _current_process_ident() != os.getpid():
        return _current_child_ident()
    else:
        return _current_process_ident()


def current_process_state() -> ProcessState:
    if _is_forking and _current_process_ident() != os.getpid():
        return _current_child_state()
    else:
        return _current_process_state()


def current_process() -> ProcessHandle:
    if _is_forking and _current_process_ident() != os.getpid():
        return _current_child()
    else:
        return _current_process()
