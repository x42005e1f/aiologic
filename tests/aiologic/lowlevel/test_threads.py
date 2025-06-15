#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: 0BSD

import weakref

from concurrent.futures import ThreadPoolExecutor

import pytest

import aiologic


def test_current_thread():
    thread1 = aiologic.lowlevel.current_thread()
    with ThreadPoolExecutor(1) as executor:
        future = executor.submit(aiologic.lowlevel.current_thread)
        thread2 = future.result()
    with ThreadPoolExecutor(1) as executor:
        future = executor.submit(aiologic.lowlevel.current_thread)
        thread3 = future.result()

    assert thread1 is not thread2
    assert thread1 is not thread3
    assert thread2 is not thread3


def _test_current_thread_on(threading):
    thread_obj = None
    thread_ident = None

    def run():
        nonlocal thread_obj
        nonlocal thread_ident

        thread_obj = aiologic.lowlevel.current_thread()
        thread_ident = aiologic.lowlevel.current_thread_ident()

    thread = threading.Thread(target=run)
    thread.start()
    thread.join()

    assert thread_obj is thread
    assert thread_ident == thread.ident


def test_current_thread_on_threading():
    threading = pytest.importorskip("threading")

    _test_current_thread_on(threading)


def test_current_thread_on_eventlet():
    try:  # see python-trio/trio#3015
        import trio  # noqa: F401
    except ImportError:
        pass

    patcher = pytest.importorskip("eventlet.patcher")

    threading = patcher.original("threading")

    _test_current_thread_on(threading)


def test_current_thread_keying():
    thread1 = aiologic.lowlevel.current_thread()
    with ThreadPoolExecutor(1) as executor:
        future = executor.submit(aiologic.lowlevel.current_thread)
        thread2 = future.result()
    with ThreadPoolExecutor(1) as executor:
        future = executor.submit(aiologic.lowlevel.current_thread)
        thread3 = future.result()

    assert len({thread1, thread2, thread3}) > 1


def test_current_thread_weakrefing():
    thread = aiologic.lowlevel.current_thread()

    assert weakref.ref(thread)() is thread


def test_current_thread_ident():
    thread1 = aiologic.lowlevel.current_thread_ident()
    with ThreadPoolExecutor(1) as executor:
        future = executor.submit(aiologic.lowlevel.current_thread_ident)
        thread2 = future.result()
    with ThreadPoolExecutor(1) as executor:
        future = executor.submit(aiologic.lowlevel.current_thread_ident)
        thread3 = future.result()

    assert thread1 != thread2
    assert thread1 != thread3
