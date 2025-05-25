#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: 0BSD

import aiologic


def test_current_green_token(spawn):
    token1 = aiologic.lowlevel.current_green_token()
    future = spawn(aiologic.lowlevel.current_green_token)
    token2 = future.wait()
    future = spawn(aiologic.lowlevel.current_green_token, separate=True)
    token3 = future.wait()

    if spawn.backend == "threading":
        assert token1 is not token2
    else:
        assert token1 is token2
    assert token1 is not token3
    assert token2 is not token3


async def test_current_async_token(spawn):
    token1 = aiologic.lowlevel.current_async_token()
    future = spawn(aiologic.lowlevel.current_async_token)
    token2 = await future
    future = spawn(aiologic.lowlevel.current_async_token, separate=True)
    token3 = await future

    assert token1 is token2
    assert token1 is not token3
    assert token2 is not token3


def test_current_green_token_ident(spawn):
    token1 = aiologic.lowlevel.current_green_token_ident()
    future = spawn(aiologic.lowlevel.current_green_token_ident)
    token2 = future.wait()
    future = spawn(aiologic.lowlevel.current_green_token_ident, separate=True)
    token3 = future.wait()

    assert token1[0] == token2[0] == token3[0] == spawn.backend
    if spawn.backend == "threading":
        assert token1 != token2
    else:
        assert token1 == token2
    assert token1 != token3


async def test_current_async_token_ident(spawn):
    token1 = aiologic.lowlevel.current_async_token_ident()
    future = spawn(aiologic.lowlevel.current_async_token_ident)
    token2 = await future
    future = spawn(aiologic.lowlevel.current_async_token_ident, separate=True)
    token3 = await future

    assert token1[0] == token2[0] == token3[0] == spawn.backend
    assert token1 == token2
    assert token1 != token3


def test_current_green_task(spawn):
    task1 = aiologic.lowlevel.current_green_task()
    future = spawn(aiologic.lowlevel.current_green_task)
    task2 = future.wait()
    future = spawn(aiologic.lowlevel.current_green_task, separate=True)
    task3 = future.wait()

    assert task1 is not task2
    assert task1 is not task3
    assert task2 is not task3


async def test_current_async_task(spawn):
    task1 = aiologic.lowlevel.current_async_task()
    future = spawn(aiologic.lowlevel.current_async_task)
    task2 = await future
    future = spawn(aiologic.lowlevel.current_async_task, separate=True)
    task3 = await future

    assert task1 is not task2
    assert task1 is not task3
    assert task2 is not task3


def test_current_green_task_ident(spawn):
    task1 = aiologic.lowlevel.current_green_task_ident()
    future = spawn(aiologic.lowlevel.current_green_task_ident)
    task2 = future.wait()
    future = spawn(aiologic.lowlevel.current_green_task_ident, separate=True)
    task3 = future.wait()

    assert task1[0] == task2[0] == task3[0] == spawn.backend
    assert task1 != task2
    assert task1 != task3


async def test_current_async_task_ident(spawn):
    task1 = aiologic.lowlevel.current_async_task_ident()
    future = spawn(aiologic.lowlevel.current_async_task_ident)
    task2 = await future
    future = spawn(aiologic.lowlevel.current_async_task_ident, separate=True)
    task3 = await future

    assert task1[0] == task2[0] == task3[0] == spawn.backend
    assert task1 != task2
    assert task1 != task3
