#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: 0BSD

import pickle

import pytest
import aiologic.lowlevel


class _TestMarker:
    def test_base(self, /):
        assert type(self.value)() is self.value  # singleton
        assert repr(self.value) == self.name
        assert not self.value

    def test_attrs(self, /):
        with pytest.raises(AttributeError):
            self.value.nonexistent_attribute
        with pytest.raises(AttributeError):
            self.value.nonexistent_attribute = 42
        with pytest.raises(AttributeError):
            del self.value.nonexistent_attribute

    def test_pickling(self, /):
        assert pickle.loads(pickle.dumps(self.value)) is self.value

    def test_inheritance(self, /):
        with pytest.raises(TypeError):

            class MarkerType(type(self.value)):
                pass


class TestNone(_TestMarker):
    name = "None"
    value = None


class TestMissing(_TestMarker):  # like None
    name = "MISSING"
    value = aiologic.lowlevel.MISSING
