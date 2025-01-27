..
  SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
  SPDX-License-Identifier: CC-BY-4.0

Why?
====

Cooperative (coroutines, greenlets) and preemptive (threads) multitasking
are not usually used together. Typically, you have an application that uses
only threads (classic application) or only coroutines/greenlets
(asynchronous application). But sometimes so different styles need to coexist.

.. code:: python

    # cooperative multitasking (deterministic execution order)

    async def foo():
        print("foo (in)")
        await asyncio.sleep(0)  # switch to bar()
        print("foo (out)")

    async def bar():
        print("bar (in)")
        await asyncio.sleep(0)  # switch to foo()
        print("bar (out)")

    async with asyncio.TaskGroup() as tg:
        tg.create_task(foo())
        tg.create_task(bar())

.. code:: python

    # preemptive multitasking (non-deterministic execution order)

    def foo():
        print("foo (in)")
        time.sleep(0)  # maybe switch to the main thread
        time.sleep(0)  # maybe switch to bar()
        print("foo (out)")

    def bar():
        print("bar (in)")
        time.sleep(0)  # maybe switch to the main thread
        time.sleep(0)  # maybe switch to foo()
        print("bar (out)")

    with ThreadPoolExecutor(2) as executor:
        executor.submit(foo)
        executor.submit(bar)

The main problem is notification when some event occurs,
since both synchronization and communication depend on it.
Cooperative-only (async-only) and preemptive-only (sync-only) worlds
already have suitable primitives, but when they collide,
things get much more complicated. Here are some of those situations
(assuming that the primary multitasking style is cooperative):

* Using a library that manages threads itself
  (e.g. a web app).
* Reusing the same worker thread for different asynchronous operations
  (e.g. to access a serial port).
* Requirement to guarantee even distribution of CPU resources
  between different groups of tasks
  (e.g. a chatbot working in multiple chats).
* Interaction of two or more frameworks
  that cannot be run in the same event loop
  (e.g. a GUI framework with any other framework).
* Parallelization of code whose synchronous part cannot be easily delegated
  to a thread pool
  (e.g. a CPU-bound network application that needs low response times).
* Simultaneous use of incompatible concurrency libraries in different threads
  (e.g. due to legacy code).
* `Accelerating asynchronous applications in a nogil world
  <https://discuss.python.org/t/asyncio-in-a-nogil-world/30694>`_.

These situations have one thing in common: you may need a way
to interact between threads, at least one of which may run an event loop.
However, you cannot use primitives from the ``threading`` module
because they block the event loop. You also cannot use primitives from
the ``asyncio`` module because they `are not thread-safe/thread-aware
<https://stackoverflow.com/a/79198672>`_.

Known solutions (only for some special cases) use one of the following ideas:

- Delegate waiting to a thread pool (executor),
  e.g. via ``run_in_executor()``.
- Delegate calling to an event loop,
  e.g. via ``call_soon_threadsafe()``.
- Perform polling via timeouts and non-blocking calls.

All these ideas have disadvantages. Polling consumes a lot of CPU resources,
actually blocks the event loop for a short time, and has poor responsiveness.
The ``call_soon_threadsafe()`` approach does not actually do any real work
until the event loop scheduler handles a callback.
The ``run_in_executor()`` approach requires a worker thread per call
and has issues with cancellation and timeouts:

.. code:: python

    import asyncio
    import threading

    from concurrent.futures import ThreadPoolExecutor

    executor = ThreadPoolExecutor(8)
    semaphore = threading.Semaphore(0)


    async def main() -> None:
        loop = asyncio.get_running_loop()

        for _ in range(8):
            future = loop.run_in_executor(executor, semaphore.acquire)

            try:
                await asyncio.wait_for(future, 0)
            except asyncio.TimeoutError:
                pass


    print("active threads:", threading.active_count())  # 1
    asyncio.run(main())
    print("active threads:", threading.active_count())  # 9 - wow, thread leak!

    # program will hang until you press Control-C

However, *aiologic* has none of these disadvantages.
Using its approach based on low-level events,
it gives you much more than you can get with alternatives.
That's why it's there, and that's why you're here.
