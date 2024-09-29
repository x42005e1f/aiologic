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
        print(f"started thread={i} task={j}")

        async with lock:
            await anyio.sleep(1)

        print(f"stopped thread={i} task={j}")


    async def main(i):
        async with anyio.create_task_group() as tasks:
            for j in range(2):
                tasks.start_soon(func, i, j)


    for i in range(2):
        Thread(target=anyio.run, args=[main, i]).start()

It prints something like this:

.. code-block::

    started thread=0 task=0
    started thread=1 task=0
    started thread=0 task=1
    started thread=1 task=1
    stopped thread=0 task=0
    stopped thread=1 task=0
    stopped thread=0 task=1
    stopped thread=1 task=1

As you can see, when using ``aiologic.Lock``, tasks from different event loops
are all able to acquire a lock. In the same case if you use ``anyio.Lock``, it
will raise a ``RuntimeError``. And ``threading.Lock`` will cause a deadlock.

Features
========

* Python 3.8+ support
* `CPython <https://www.python.org/>`_ and `PyPy <https://pypy.org/>`_ support
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

Synchronization primitives:

* Semaphores: counting and bounded
* Locks: primitive, ownable and reentrant
* Capacity limiters
* Conditions
* Barriers: single-use only
* Events: one-time and reusable
* Resource guards

Communication primitives:

* Queues: FIFO and LIFO

Supported concurrency libraries:

* `asyncio <https://docs.python.org/3/library/asyncio.html>`_
  and `trio <https://trio.readthedocs.io>`_ (coroutine-based)
* `eventlet <https://eventlet.readthedocs.io>`_
  and `gevent <https://www.gevent.org/>`_ (greenlet-based)

All synchronization primitives are implemented entirely on effectively atomic
operations, which gives `an incredible speedup on PyPy
<https://gist.github.com/x42005e1f/149d3994d5f7bd878def71d5404e6ea4>`_ compared
to alternatives from the threading module. All this works because of GIL, but
per-object locks also ensure that `the same operations are still atomic
<https://peps.python.org/pep-0703/#container-thread-safety>`_, so aiologic also
works when running in a `free-threaded mode
<https://docs.python.org/3.13/whatsnew/3.13.html#free-threaded-cpython>`_.
