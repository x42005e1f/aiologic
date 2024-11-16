#!/usr/bin/env python3

import pickle

import pytest
import aiologic.lowlevel


def test_none():
    assert type(None)() is None
    assert pickle.loads(pickle.dumps(None)) is None
    assert repr(None) == "None"
    assert not None

    with pytest.raises(TypeError):

        class NoneType(type(None)):
            pass


def test_missing():  # like None
    MISSING = aiologic.lowlevel.MISSING

    assert type(MISSING)() is MISSING
    assert pickle.loads(pickle.dumps(MISSING)) is MISSING
    assert repr(MISSING) == "MISSING"
    assert not MISSING

    with pytest.raises(TypeError):

        class MissingType(type(MISSING)):
            pass
