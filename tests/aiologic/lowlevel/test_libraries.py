#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: 0BSD

from functools import partial

import pytest

import aiologic


def test_current_green_library(spawn):
    lib1 = aiologic.lowlevel.current_green_library()
    lib2 = aiologic.lowlevel.current_green_library(failsafe=False)
    lib3 = aiologic.lowlevel.current_green_library(failsafe=True)

    assert lib1 == lib2 == lib3 == spawn.backend


async def test_current_async_library(spawn):
    lib1 = aiologic.lowlevel.current_async_library()
    lib2 = aiologic.lowlevel.current_async_library(failsafe=False)
    lib3 = aiologic.lowlevel.current_async_library(failsafe=True)

    assert lib1 == lib2 == lib3 == spawn.backend


async def test_current_green_library_failsafe(spawn):
    try:
        library = aiologic.lowlevel.current_green_library()
    except aiologic.lowlevel.GreenLibraryNotFoundError:
        pass
    else:
        assert library == "threading"

    try:
        library = aiologic.lowlevel.current_green_library(failsafe=False)
    except aiologic.lowlevel.GreenLibraryNotFoundError:
        pass
    else:
        assert library == "threading"

    library = aiologic.lowlevel.current_green_library(failsafe=True)
    assert library is None or library == "threading"


def test_current_async_library_failsafe(spawn):
    with pytest.raises(aiologic.lowlevel.AsyncLibraryNotFoundError):
        aiologic.lowlevel.current_async_library()

    with pytest.raises(aiologic.lowlevel.AsyncLibraryNotFoundError):
        aiologic.lowlevel.current_async_library(failsafe=False)

    assert aiologic.lowlevel.current_async_library(failsafe=True) is None


def test_current_green_library_threadsafe(spawn, test_thread_safety):
    test_thread_safety(
        partial(spawn, test_current_green_library, spawn),
        test_current_green_library_tlocal,
    )


async def test_current_async_library_threadsafe(spawn, test_thread_safety):
    await test_thread_safety(
        partial(spawn, test_current_async_library, spawn),
        test_current_async_library_tlocal,
    )


def test_current_green_library_tlocal():
    assert aiologic.lowlevel.current_green_library_tlocal.name is None
    aiologic.lowlevel.current_green_library_tlocal.name = "somelet"

    try:
        assert aiologic.lowlevel.current_green_library() == "somelet"
    finally:
        aiologic.lowlevel.current_green_library_tlocal.name = None


def test_current_async_library_tlocal():
    assert aiologic.lowlevel.current_async_library_tlocal.name is None
    aiologic.lowlevel.current_async_library_tlocal.name = "someio"

    try:
        assert aiologic.lowlevel.current_async_library() == "someio"
    finally:
        aiologic.lowlevel.current_async_library_tlocal.name = None
