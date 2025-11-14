#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: 0BSD

from __future__ import annotations

import asyncio

import pytest

from aiologic import (
    LifoQueue,
    PriorityQueue,
    Queue,
    QueueShutdown,
    SimpleQueue,
)


@pytest.fixture(params=(Queue, SimpleQueue, PriorityQueue, LifoQueue), ids=str)
def queue_type(
    request: pytest.FixtureRequest,
) -> type[SimpleQueue | Queue]:
    return request.param  # type: ignore[no-any-return]


def test_shutdown(queue_type: type[SimpleQueue | Queue]) -> None:
    async def handler(q: type[SimpleQueue | Queue]) -> bool:
        try:
            while True:
                await q.async_get()
        except QueueShutdown:
            return True

    async def main():
        q = queue_type()
        task = asyncio.create_task(handler(q))
        await q.async_put(1)
        await q.async_put(2)
        q.shutdown()
        assert await asyncio.wait_for(task, 2)

    asyncio.run(main())
