import asyncio

from typing import Union

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
) -> Union[type[SimpleQueue], type[Queue]]:
    return request.param  # type: ignore[no-any-return]


def test_shutdown(queue_type: Union[type[SimpleQueue], type[Queue]]):

    async def handler(q: Union[type[SimpleQueue], type[Queue]]):
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
        await asyncio.wait_for(task, 2)

    asyncio.run(main())
