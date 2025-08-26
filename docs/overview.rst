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
*Harder* than just thread-safe `asyncio primitives <https://docs.python.org/3/
library/asyncio-sync.html#asyncio-sync>`__. *Better* than `AnyIO primitives
<https://anyio.readthedocs.io/en/stable/synchronization.html>`__. *Faster* than
`Curio's universal synchronization <https://curio.readthedocs.io/en/latest/
reference.html#universal-synchronizaton>`__. *Stronger* than separate
solutions.

Features
--------

There are many features common to the entire library. Below is a brief
description of just a few of them. If you want to know more, please read the
rest of the documentation.

Versatility
+++++++++++

Every primitive can be used as:

1. **Single-library:** you can use it with a single library, like a standard
   primitive or native to a third-party library (but better?).
2. **Multi-library/single-threaded:** you can use it with multiple libraries
   combined in some tricky way in a single thread (such as `the asyncio hub in
   eventlet <https://eventlet.readthedocs.io/en/stable/asyncio/
   migration.html>`__, `asyncio-gevent <https://github.com/gfmio/
   asyncio-gevent>`__, or `trio-asyncio <https://github.com/python-trio/
   trio-asyncio>`__).
3. **Multi-library/multi-threaded:** you can use it with multiple libraries
   running in different threads (even with multiple event loops!).

And also every primitive is:

1. **Async-aware:** it is designed to support asynchronous libraries (there is
   async/await!).
2. **Thread-aware:** it is designed to support threads (regardless of the
   interface used!).
3. **Greenlet-aware:** it is designed to support greenlet-based libraries (both
   with and without monkey patching!).

But the versatility does not end there.

Safety
++++++

Unless explicitly stated otherwise, *everything* in aiologic is:

1. **Thread-safe:** you can freely call the same functions and methods in
   different threads (even with `free-threading <https://docs.python.org/3/
   howto/free-threading-python.html>`__!).
2. **Coroutine-safe:** you can freely call the same functions and methods in
   different tasks within the same thread (even with `greenlets <https://
   greenlet.readthedocs.io/en/stable/>`__!).
3. **Cancellation-safe:** you can freely cancel any blocking call at any point
   in time without the risk of data loss or other unpleasant things (but this
   does not mean that you will not lose your place in the waiting queue — a
   note for those who came from `Tokio <https://tokio.rs/>`__).

Neither standard nor native primitives have all three guarantees.

.. note::

    There is also *async-signal-safety*, also known as just *reentrancy*.
    Functions with this property can be safely called from inside a signal
    handler or destructor (which can be called after any bytecode instruction).

    You may find that :meth:`queue.SimpleQueue.put` is reentrant, but only when
    implemented at the C level, and only that one. No primitive from the
    :mod:`threading` module provides reentrant functions (at least those
    implemented at the Python level).

    Yes, as you may have guessed, aiologic has a different situation. Due to
    its design (lockless, lock-free, thread-safe, etc.) almost all of its
    functions are potentially reentrant (which makes aiologic primitives even
    more unique). But there are some caveats that are beyond the scope of this
    overview.
