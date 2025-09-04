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

Reentrancy
++++++++++

Let us give the following definitions:

1. **A reentrant primitive** is a primitive that can be safely reused
   (reacquired) by the same execution unit after it has already been used
   (acquired). For example, :class:`threading.Lock` is not reentrant because
   calling :meth:`acquire() <threading.Lock.acquire>` twice will result in a
   deadlock, but :class:`threading.RLock` is reentrant.
2. **A reentrant function**, also known as *an async-signal-safe function*, is
   a function that can be safely called from inside a signal handler or
   destructor (which can be called after any bytecode instruction). For
   example, :meth:`queue.SimpleQueue.put` is reentrant, but only when
   implemented at the C level, and only that one.
3. **A signal-safe primitive** is a primitive whose functions are all
   reentrant. For example, no primitive from the :mod:`threading` module
   (except :class:`threading.Lock`) is signal-safe, because attempting to use a
   primitive while interrupted in any of its methods can lead to a deadlock or
   broken behavior, even for non-blocking calls, even with
   :class:`threading.RLock`.

Due to its design (lockless, lock-free, thread-safe, etc.), aiologic boasts
both reentrant and signal-safe primitives. You may find that
:class:`aiologic.RLock` is a reentrant lock, and
:class:`aiologic.RCapacityLimiter` is, when compared to standard primitives, a
reentrant semaphore. And what about signal-safety...

The following primitives work as expected in conditions requiring
signal-safety:

* Events: all (including low-level)
* Semaphores: unbounded only (both counting and binary)
* Queues: simple only (both FIFO and LIFO)
* Flags (nothing to say)
* Resource guards (but does this make sense?)

All others may behave unexpectedly (for example, you will not be able to put
items into a complex queue that is in use, and sometimes you will not even be
able to reacquire a reentrant capacity limiter or lock), but they still remain
functional inside signal handlers and destructors. In particular, all
non-blocking calls remain non-blocking and do not lead to deadlocks or any
other undesirable things.

.. caution::

    By default, low-level waiters (via which all of the above-mentioned
    blocking primitives operate!) are not signal-safe for all libraries except
    threading, when tasks wait in the same thread (in the case of signal
    handlers, :ref:`in the main thread <signals-and-threads>`). This is because
    when using primitives in a single thread, fast local ways of waking up
    tasks are used, which are not thread-safe and certainly not signal-safe.

    If you want to use signal handlers or destructors to wake up, for example,
    asyncio tasks, you can apply :func:`aiologic.lowlevel.enable_signal_safety`
    to your function or code block:

    .. code:: python

        import asyncio
        import signal

        import aiologic


        async def main():
            signalled = aiologic.Event()

            @aiologic.lowlevel.enable_signal_safety
            def handler(signum, frame):
                signalled.set()

            # set the signal handler and a 1-second alarm
            signal.signal(signal.SIGALRM, handler)
            signal.alarm(1)

            print("before")
            await signalled  # waits for the alarm
            print("after")


        asyncio.run(main())

        # program will end in 1 second
