#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: 0BSD

import time

from collections import deque


def test_deque_popleft_and_append_threadsafe(test_thread_safety):
    queue = deque([object])

    def f():
        try:
            value = queue.popleft()
        except IndexError:
            time.sleep(0)
        else:
            assert not queue
            queue.append(value)

    test_thread_safety(f, f)

    assert len(queue) == 1


def test_deque_getitem_and_remove_threadsafe(test_thread_safety):
    queue = deque([object])

    def f():
        try:
            value = queue[0]
        except IndexError:
            time.sleep(0)
        else:
            try:
                queue.remove(value)
            except ValueError:
                assert value not in queue
            else:
                assert not queue
                queue.append(object())

    test_thread_safety(f, f)

    assert len(queue) == 1
