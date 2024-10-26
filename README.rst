========
aiologic
========

**aiologic** is an async-aware library for tasks synchronization and their
communication in different threads and different event loops. Let's take a look
at the example:

.. code:: python

    from threading import Thread

    import anyio

    from aiologic import Lock

    lock = Lock()


    async def func(i, j):
        print(f"thread={i} task={j} started")

        async with lock:
            await anyio.sleep(1)

        print(f"thread={i} task={j} stopped")


    async def main(i):
        async with anyio.create_task_group() as tasks:
            for j in range(2):
                tasks.start_soon(func, i, j)


    for i in range(2):
        Thread(target=anyio.run, args=[main, i]).start()

It prints something like this:

.. code-block::

    thread=0 task=0 started
    thread=1 task=0 started
    thread=0 task=1 started
    thread=1 task=1 started
    thread=0 task=0 stopped
    thread=1 task=0 stopped
    thread=0 task=1 stopped
    thread=1 task=1 stopped

As you can see, when using ``aiologic.Lock``, tasks from different event loops
are all able to acquire a lock. In the same case if you use ``anyio.Lock``, it
will raise a ``RuntimeError``. And ``threading.Lock`` will cause a deadlock.

Why?
====

Cooperative (coroutines, greenlets) and preemptive (threads) multitasking are
not usually used together. But there are situations when these so different
styles need to coexist:

* Interaction of two or more frameworks that cannot be run in the same event
  loop (e.g. a GUI framework with any other framework).
* Parallelization of code whose synchronous part cannot be easily delegated to
  a thread pool (e.g. a CPU-bound network application that needs low
  response times).
* Simultaneous use of incompatible concurrency libraries in different threads
  (e.g. due to legacy code).

Known solutions (only for some special cases) use one of the following ideas:

- Delegate waiting to a thread pool (executor), e.g. via ``run_in_executor()``.
- Delegate calling to an event loop, e.g. via
  ``call_soon_threadsafe()``.
- Perform polling via timeouts and non-blocking calls.

All these ideas have disadvantages. Polling consumes a lot of CPU resources,
actually blocks the event loop for a short time, and has poor responsiveness.
The ``call_soon_threadsafe()`` approach does not actually do any real work
until the event loop scheduler handles a callback, and in the case of a queue
only works when there is only one consumer. The ``run_in_executor()`` approach
requires a worker thread per call and has issues with cancellation and
timeouts:

.. code:: python

    import asyncio
    import threading

    from concurrent.futures import ThreadPoolExecutor

    executor = ThreadPoolExecutor(8)
    semaphore = threading.Semaphore(0)


    async def main():
        loop = asyncio.get_running_loop()

        for _ in range(8):
            try:
                await asyncio.wait_for(loop.run_in_executor(
                    executor,
                    semaphore.acquire,
                ), 0)
            except asyncio.TimeoutError:
                pass


    print('active threads:', threading.active_count())  # 1

    asyncio.run(main())

    print('active threads:', threading.active_count())  # 9 - wow, thread leak!

    # program will hang until you press Control-C

However, *aiologic* has none of these disadvantages. Using its approach based
on low-level events, it gives you much more than you can get with alternatives.
That's why it's there, and that's why you're here.

Features
========

* Python 3.8+ support
* `CPython <https://www.python.org/>`_ and `PyPy <https://pypy.org/>`_ support
* Pickling and weakrefing support
* Cancellation and timeouts support
* Optional `Trio-style checkpoints
  <https://trio.readthedocs.io/en/stable/reference-core.html#checkpoints>`_:

  * enabled by default for Trio itself
  * disabled by default for all others

* Only one checkpoint per asynchronous call:

  * exactly one context switch if checkpoints are enabled
  * zero or one context switch if checkpoints are disabled

* Fairness wherever possible (with some caveats)
* Thread safety wherever possible
* Zero required dependencies
* Lock-free implementation

Synchronization primitives:

* Semaphores: counting and bounded
* Locks: primitive, ownable and reentrant
* Capacity limiters: simple and reentrant
* Condition variables
* Barriers: single-use and cyclic
* Events: one-time, reusable and countdown
* Resource guards

Communication primitives:

* Queues: FIFO, LIFO and priority

Supported concurrency libraries:

* `asyncio <https://docs.python.org/3/library/asyncio.html>`_
  and `trio <https://trio.readthedocs.io>`_ (coroutine-based)
* `eventlet <https://eventlet.readthedocs.io>`_
  and `gevent <https://www.gevent.org/>`_ (greenlet-based)

All synchronization and communication primitives are implemented entirely on
effectively atomic operations, which gives `an incredible speedup on PyPy
<https://gist.github.com/x42005e1f/149d3994d5f7bd878def71d5404e6ea4>`_ compared
to alternatives from the threading module. All this works because of GIL, but
per-object locks also ensure that `the same operations are still atomic
<https://peps.python.org/pep-0703/#container-thread-safety>`_, so aiologic also
works when running in a `free-threaded mode
<https://docs.python.org/3.13/whatsnew/3.13.html#free-threaded-cpython>`_.
