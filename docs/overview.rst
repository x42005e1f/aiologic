..
  SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
  SPDX-License-Identifier: CC-BY-4.0

Overview
========

The aiologic library has primitives similar to existing ones:

.. tab:: aiologic.Lock

  .. code:: python

    import anyio

    import aiologic


    async def work(lock):
        async with lock:
            await anyio.sleep(1)  # do some work


    async def main():
        lock = aiologic.Lock()

        async with anyio.create_task_group() as tg:
            for _ in range(3):
                tg.start_soon(work, lock)


    anyio.run(main)

    # program will end in 3 seconds

.. tab:: anyio.Lock

  .. code:: python

    import anyio

    # import aiologic


    async def work(lock):
        async with lock:
            await anyio.sleep(1)  # do some work


    async def main():
        lock = anyio.Lock()

        async with anyio.create_task_group() as tg:
            for _ in range(3):
                tg.start_soon(work, lock)


    anyio.run(main)

    # program will end in 3 seconds

.. tab:: trio.Lock

  .. code:: python

    import trio

    # import aiologic


    async def work(lock):
        async with lock:
            await trio.sleep(1)  # do some work


    async def main():
        lock = trio.Lock()

        async with trio.open_nursery() as nursery:
            for _ in range(3):
                nursery.start_soon(work, lock)


    trio.run(main)

    # program will end in 3 seconds

.. tab:: asyncio.Lock

  .. code:: python

    import asyncio

    # import aiologic


    async def work(lock):
        async with lock:
            await asyncio.sleep(1)  # do some work


    async def main():
        lock = asyncio.Lock()

        async with asyncio.TaskGroup() as tg:
            for _ in range(3):
                tg.create_task(work(lock))


    asyncio.run(main())

    # program will end in 3 seconds

And those that are inspired by some libraries but can be used with other ones:

.. tab:: aiologic.RLock

  .. code:: python

    import anyio

    import aiologic


    async def work(lock, n):
        async with lock:
            if n > 0:
                await work(lock, n - 1)  # re-enter
            else:
                await anyio.sleep(1)  # do some work


    async def main():
        lock = aiologic.RLock()

        async with anyio.create_task_group() as tg:
            for _ in range(5):
                tg.start_soon(work, lock, 3)


    anyio.run(main)

    # program will end in 5 seconds

.. tab:: gevent.lock.RLock

  .. code:: python

    import gevent

    import gevent.lock


    def work(lock, n):
        with lock:
            if n > 0:
                work(lock, n - 1)  # re-enter
            else:
                gevent.sleep(1)  # do some work


    def main():
        lock = gevent.lock.RLock()

        greenlets = [gevent.spawn(work, lock, 3) for _ in range(5)]

        gevent.joinall(greenlets)


    main()

    # program will end in 5 seconds

Meanwhile, one of the unique features of aiologic is that primitives can be
used by anyone at the same time. For example, you can limit access to a shared
resource using a capacity limiter for both `gevent <https://www.gevent.org/>`__
and `asyncio <https://docs.python.org/3/library/asyncio.html>`__ within the
same process. And it will just work, just like magic!

.. code:: python

    import asyncio

    from threading import Thread

    import gevent

    import aiologic

    limiter = aiologic.CapacityLimiter(2)


    def green_work():
        with limiter:
            gevent.sleep(1)  # do some work


    async def async_work():
        async with limiter:
            await asyncio.sleep(1)  # do some work


    def green_main():
        greenlets = [gevent.spawn(green_work) for _ in range(7)]

        gevent.joinall(greenlets)


    async def async_main():
        tasks = [asyncio.create_task(async_work()) for _ in range(7)]

        await asyncio.gather(*tasks)


    Thread(target=green_main).start()
    Thread(target=asyncio.run, args=[async_main()]).start()

    # program will end in 7 seconds

However, because of their two-faced nature, primitives do not offer API-level
compatibility. Methods are prefixed:

* with ``green_`` for "green" libraries (without async/await syntax)
* with ``async_`` for "async" libraries (with async/await syntax)

And the exception is the wait methods:

* ``primitive.wait()`` for "green" libraries (without async/await syntax)
* ``await primitive`` for "async" libraries (with async/await syntax)

.. note::

    Despite their name, methods prefixed with ``green_`` support not only
    greenlets but also threads. They are called so because they switch to a hub
    when it is detected in the current thread. Unless you use `eventlet
    <https://eventlet.readthedocs.io>`__ or `gevent <https://
    www.gevent.org/>`__, they behave like "sync" methods!

The aiologic library aims to be the best locking library as far as it can be.
Harder than just thread-safe `asyncio primitives <https://docs.python.org/3/
library/asyncio-sync.html#asyncio-sync>`__. Better than `AnyIO primitives
<https://anyio.readthedocs.io/en/stable/synchronization.html>`__. Faster than
`Curio's universal synchronization <https://curio.readthedocs.io/en/latest/
reference.html#universal-synchronizaton>`__. And stronger than separate
solutions.
