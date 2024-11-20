#!/usr/bin/env python3

import pytest


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
        "thread_safety: mark test as thread-safety test",
    )


def pytest_collection_modifyitems(config, items):
    for item in items:
        if item.nodeid.endswith("_thread_safety"):
            item.add_marker(pytest.mark.thread_safety)

        if "thread_safety" in item.keywords:
            if not config.getoption("--thread-safety"):
                item.add_marker(
                    pytest.mark.skip(
                        reason="need --thread-safety option to run",
                    )
                )
