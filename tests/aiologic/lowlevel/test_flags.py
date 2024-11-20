#!/usr/bin/env python3

import pickle

import pytest
import aiologic.lowlevel


class TestFlag:
    factory = aiologic.lowlevel.Flag

    def test_base(self, /):
        with pytest.raises(LookupError):
            self.factory().get()
        assert self.factory(None).get() is None
        assert self.factory(marker="marker").get() == "marker"

        assert repr(self.factory()) == "Flag()"
        assert repr(self.factory(None)) == "Flag(None)"
        assert repr(self.factory(marker="marker")) == "Flag('marker')"

        assert not self.factory()
        assert self.factory(None)
        assert self.factory(marker="marker")

        assert self.factory() != self.factory()
        assert self.factory(None) != self.factory(None)
        assert self.factory("marker") != self.factory("marker")

    def test_attrs(self, /):
        flag = self.factory()

        with pytest.raises(AttributeError):
            flag.nonexistent_attribute
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

        assert not flag

        copy1 = pickle.loads(pickle.dumps(flag))
        copy2 = pickle.loads(pickle.dumps(flag))

        assert not flag
        assert not copy1
        assert not copy2

        copy1.set()

        assert not flag
        assert copy1
        assert not copy2

        flag.set()

        assert flag
        assert copy1
        assert not copy2
