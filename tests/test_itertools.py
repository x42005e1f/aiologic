#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: 0BSD

from itertools import count


def test_count_threadsafe(test_thread_safety):
    it = count()

    c1 = 0
    c2 = 0

    def a():
        nonlocal c1

        next(it)

        c1 += 1

    def b():
        nonlocal c2

        next(it)

        c2 += 1

    test_thread_safety(a, b)

    assert c1 + c2 == next(it)
