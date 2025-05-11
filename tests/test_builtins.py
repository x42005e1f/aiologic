#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: 0BSD

import sys
import time

import pytest

try:
    from sys import _is_gil_enabled
except ImportError:
    GIL_DISABLED = False
else:
    GIL_DISABLED = not _is_gil_enabled()

GH_127266 = GIL_DISABLED
GH_129107 = GIL_DISABLED and sys.version_info <= (3, 14)


@pytest.mark.skipif(GH_127266, reason="python/cpython#127266")
def test_type_slots_threadsafe(test_thread_safety):
    class MyClass:
        __slots__ = ("attr",)

    obj = MyClass()
    obj.attr = object()

    def f():
        try:
            del obj.attr
        except AttributeError:
            time.sleep(0)
        else:
            assert not hasattr(obj, "attr")
            obj.attr = object()

    test_thread_safety(f, f)

    assert hasattr(obj, "attr")


def test_dict_delitem_and_setitem_threadsafe(test_thread_safety):
    dct = {"key": "value"}

    def f():
        try:
            del dct["key"]
        except KeyError:
            time.sleep(0)
        else:
            assert "key" not in dct
            dct["key"] = "value"

    test_thread_safety(f, f)

    assert "key" in dct


def test_set_remove_and_add_threadsafe(test_thread_safety):
    st = {"value"}

    def f():
        try:
            st.remove("value")
        except KeyError:
            time.sleep(0)
        else:
            assert "value" not in st
            st.add("value")

    test_thread_safety(f, f)

    assert "value" in st


def test_list_pop_and_append_threadsafe(test_thread_safety):
    lst = [object()]

    def f():
        try:
            value = lst.pop()
        except IndexError:
            time.sleep(0)
        else:
            assert not lst
            lst.append(value)

    test_thread_safety(f, f)

    assert len(lst) == 1


@pytest.mark.skipif(GH_129107, reason="python/cpython#129107")
def test_bytearray_pop_and_append_threadsafe(test_thread_safety):
    array = bytearray(1)

    def f():
        try:
            value = array.pop()
        except IndexError:
            time.sleep(0)
        else:
            assert not array
            array.append(value)

    test_thread_safety(f, f)

    assert len(array) == 1
