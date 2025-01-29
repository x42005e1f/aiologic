..
  SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
  SPDX-License-Identifier: CC-BY-4.0

Why?
====

Cooperative (coroutines, greenlets) and preemptive (threads) multitasking
are not usually used together. Typically, you have an application that uses
only threads (classic application) or only coroutines/greenlets
(asynchronous application). But sometimes so different styles need to coexist.

.. tab:: cooperative multitasking (coroutines)

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

.. tab:: preemptive multitasking (threads)

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
However, you cannot use primitives from the :mod:`threading` module
because they block the event loop. You also cannot use primitives from
the :mod:`asyncio` module because they `are not thread-safe/thread-aware
<https://stackoverflow.com/a/79198672>`_.

Known solutions (only for some special cases) use one of the following ideas:

- Delegate waiting to a thread pool (executor),
  e.g. via :meth:`~asyncio.loop.run_in_executor`.
- Delegate calling to an event loop,
  e.g. via :meth:`~asyncio.loop.call_soon_threadsafe`.
- Perform polling via timeouts and non-blocking calls.

All these ideas have disadvantages. Polling consumes a lot of CPU resources,
actually blocks the event loop for a short time, and has poor responsiveness.
The :meth:`~asyncio.loop.call_soon_threadsafe` approach does not actually do
any real work until the event loop scheduler handles a callback.
The :meth:`~asyncio.loop.run_in_executor` approach requires
a worker thread per call and has issues with cancellation and timeouts:

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
That's why it's there.

Relevance
---------

Despite all of aiologic's features and the complexity of the problems
it solves, it would not make sense if no one used it.
With this subsection I want to show that aiologic is not only
an interesting puzzle for its author (because it really is),
but also a tool that can solve *real problems*.
I think Stack Overflow's related questions are good enough for this purpose.

The first related questions found on Stack Overflow predate
the introduction of the :mod:`asyncio` module in Python 3.4.
These are questions about mixing greenlets and threads:

* **(2012-03-09)** `Is it safe to mix green threads and native threads
  in a single python process?
  <https://stackoverflow.com/q/9639466>`_
* **(2013-05-29)** `Can Gevent be used in combination with real threads
  in CPython?
  <https://stackoverflow.com/q/16811982>`_

But none of these questions address the problem of interaction between threads.
Such a question was only asked in 2014, a few weeks before
`the Python 3.4 release
<https://www.python.org/downloads/release/python-340/>`_,
and another question was asked the following year:

* **(2014-03-01)** `Share gevent locks/semaphores between ThreadPool threads?
  <https://stackoverflow.com/q/22108576>`_
* **(2015-02-13)** `How to combine python asyncio with threads?
  <https://stackoverflow.com/q/28492103>`_

And although they have such nice titles, the actual problems are unrelated:
in the first case, importing the :mod:`logging` module before monkey patching
is enough to solve the problem, while in the second, interaction with asyncio
is only required if the asker considers an implicit thread-safety issue.

The really related questions started to be asked in 2015 after
`the Python 3.5 release
<https://www.python.org/downloads/release/python-350/>`_.
There were two questions that year, the first about a serial device
and the second about a serial port:

* **(2015-10-01)** `Is there a way to use asyncio.Queue in multiple threads?
  <https://stackoverflow.com/q/32889527>`_
* **(2015-10-07)** `asyncio: Wait for event from other thread
  <https://stackoverflow.com/q/33000200>`_

So back in 2015, the real need for thread-safe primitives was visible.
Curiously, the first `Janus <https://github.com/aio-libs/janus>`_
(thread-safe asyncio-aware queue) release,
version `0.1.0 <https://github.com/aio-libs/janus/releases/tag/v0.1.0>`_,
was published on June 11, 2015 - before October 1, 2015,
when the related question was asked.

Since then, more and more questions have appeared. Here are just some of them:

* **(2016-05-14)** `Python asyncio wait for threads
  <https://stackoverflow.com/q/37223846>`_
* **(2017-04-03)** `python asyncio: how to best use lock threads?
  <https://stackoverflow.com/q/43195459>`_
* **(2018-09-24)** `How can I share asyncio.Queue between multiple threads?
  <https://stackoverflow.com/q/52474282>`_
* **(2018-11-05)** `How can I synchronize asyncio with other OS threads?
  <https://stackoverflow.com/q/53158101>`_
* **(2019-04-24)** `How to communicate between traditional thread
  and asyncio thread in Python?
  <https://stackoverflow.com/q/55829852>`_
* **(2019-07-16)** `Asyncio threadsafe primitives
  <https://stackoverflow.com/q/57055384>`_
* **(2020-01-08)** `Communication between async tasks and synchronous threads
  in python
  <https://stackoverflow.com/q/59650243>`_
* **(2020-08-14)** `How to use threading.Lock in async function
  while object can be accessed from multiple thread
  <https://stackoverflow.com/q/63420413>`_
* **(2024-08-30)** `Python Async Thread-safe Semaphore
  <https://stackoverflow.com/q/78932535>`_

And outside of the asyncio ecosystem, too:

* **(2018-09-23)** `Python: ways to synchronize trio tasks and regular threads
  <https://stackoverflow.com/q/52468911>`_
* **(2022-12-23)** `How to receive data from python Thread in a greenlet
  without blocking all greenlets?
  <https://stackoverflow.com/q/74903753>`_

Until now, there has been no universal library for all of these questions.
Now there is.
