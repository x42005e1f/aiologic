#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: 0BSD

import inspect
import sys

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import chain
from pathlib import Path

import pytest

from wrapt import decorator

import aiologic

if sys.version_info >= (3, 11):
    WaitTimeout = TimeoutError
else:
    from concurrent.futures import TimeoutError as WaitTimeout


def _test_thread_safety_impl(*functions):
    with ThreadPoolExecutor(len(functions)) as executor:
        barrier = aiologic.Latch(len(functions) + 1)
        stopped = aiologic.lowlevel.Flag()

        @decorator
        def wrapper(wrapped, instance, args, kwargs):
            barrier.wait()

            if "stopped" in inspect.signature(wrapped).parameters:
                while not stopped:
                    wrapped(*args, stopped=stopped, **kwargs)
            else:
                while not stopped:
                    wrapped(*args, **kwargs)

        interval = sys.getswitchinterval()
        sys.setswitchinterval(min(1e-6, interval))

        try:
            futures = [executor.submit(wrapper(f)) for f in functions]
            barrier.wait()

            try:
                for future in as_completed(futures, timeout=6):
                    future.result()  # reraise
            except WaitTimeout:
                pass
        finally:
            sys.setswitchinterval(interval)
            stopped.set()


@pytest.fixture(scope="session")
def test_thread_safety():
    return _test_thread_safety_impl


def pytest_addoption(parser):
    parser.addoption(
        "--thread-safety",
        action="store_true",
        default=False,
        help="run thread-safety tests",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "threadsafe: mark test as thread-safety test",
    )


def pytest_collection_modifyitems(config, items):
    directory = Path(__file__).parent
    ordered_tests = defaultdict(
        list,
        {
            "test_builtins": [],
            "test_collections": [],
            "test_itertools": [],
            "aiologic.lowlevel.test_markers": [],
            "aiologic.test_flags": [],
        },
    )

    for item in items:
        module_name = ".".join(item.path.relative_to(directory).parts)[:-3]
        ordered_tests[module_name].append(item)

        if "test_thread_safety" in item.fixturenames:
            item.add_marker(pytest.mark.threadsafe)

        if "threadsafe" in item.keywords:
            if not config.getoption("--thread-safety"):
                item.add_marker(
                    pytest.mark.skip(
                        reason="need --thread-safety option to run",
                    )
                )

    items[:] = chain.from_iterable(ordered_tests.values())
