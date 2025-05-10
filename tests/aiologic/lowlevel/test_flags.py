#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: 0BSD

import pickle
import time

import pytest

import aiologic

try:
    from sys import _is_gil_enabled
except ImportError:
    GIL_DISABLED = False
else:
    GIL_DISABLED = not _is_gil_enabled()


class TestFlag:
    factory = aiologic.lowlevel.Flag

    def test_base(self, /):
        with pytest.raises(LookupError):
            self.factory().get()
        assert self.factory(None).get() is None
        assert self.factory(marker="marker").get() == "marker"

        pkg = "aiologic.lowlevel"
        assert repr(self.factory()) == f"{pkg}.Flag()"
        assert repr(self.factory(None)) == f"{pkg}.Flag(None)"
        assert repr(self.factory(marker="marker")) == f"{pkg}.Flag('marker')"

        assert not self.factory()
        assert self.factory(None)
        assert self.factory(marker="marker")

        assert self.factory() != self.factory()
        assert self.factory(None) != self.factory(None)
        assert self.factory("marker") != self.factory("marker")

    def test_attrs(self, /):
        flag = self.factory()

        with pytest.raises(AttributeError):
            flag.nonexistent_attribute  # noqa: B018
        with pytest.raises(AttributeError):
            flag.nonexistent_attribute = 42
        with pytest.raises(AttributeError):
            del flag.nonexistent_attribute

    def test_get_and_set(self, /):
        flag = self.factory()

        with pytest.raises(LookupError):
            flag.get()
        assert flag.get(None) is None
        assert flag.get(default="marker") == "marker"
        assert flag.get(default_factory=list) == []

        flag.set(marker := object())

        assert flag.get() is marker
        assert flag.get(None) is marker
        assert flag.get(default="marker") is marker
        assert flag.get(default_factory=list) is marker

    def test_set_and_clear(self, /):
        flag = self.factory()

        assert not flag

        assert flag.set()
        assert not flag.set()

        assert flag

        flag.clear()

        assert not flag

        assert flag.set(1)
        assert not flag.set(2)

        assert flag.get() == 1

    def test_double_clear(self, /):
        flag = self.factory(object())

        assert flag

        flag.clear()
        flag.clear()

        assert not flag

    def test_pickling(self, /):
        flag = self.factory()
        copy = pickle.loads(pickle.dumps(flag))

        assert not flag
        assert not copy

        copy.set()

        assert not flag
        assert copy

        copy = pickle.loads(pickle.dumps(flag))

        assert not flag
        assert not copy

        flag.set()

        assert flag
        assert not copy

        copy = pickle.loads(pickle.dumps(flag))

        assert flag
        assert copy

        copy.clear()

        assert flag
        assert not copy

        copy = pickle.loads(pickle.dumps(flag))

        assert flag
        assert copy

        flag.clear()

        assert not flag
        assert copy

    def test_base_threadsafe(self, test_thread_safety):
        flag = self.factory()

        def f():
            marker = repr(flag)

            if flag or not flag.set(marker):
                flag.clear()

        test_thread_safety(f, f)

    def test_set_and_get_threadsafe(self, test_thread_safety):
        flag = self.factory()

        def a():
            if flag.set(marker := object()):
                assert flag.get(marker) is marker
            else:
                assert flag.get(None) is not marker

        def b():
            flag.clear()
            time.sleep(0)

        test_thread_safety(a, b)

    def test_set_and_clear_threadsafe(self, test_thread_safety):
        flag = self.factory()

        def a():
            flag.set()

        def b():
            flag.clear()

        test_thread_safety(a, b)

    @pytest.mark.skipif(GIL_DISABLED, reason="SIGSEGV when GIL is disabled")
    def test_pickling_threadsafe(self, test_thread_safety):
        flag = self.factory()

        def a():
            flag.set("something")
            pickle.dumps(flag)

        def b():
            flag.clear()
            time.sleep(0)

        test_thread_safety(a, b)
