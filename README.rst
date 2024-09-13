========
aiologic
========

**aiologic** is an async-aware library for synchronization and communication
between tasks in different threads and different event loops. Just look at this
example:

.. code:: python

    import time
    
    from threading import Thread, get_ident
    
    import anyio
    
    from aiologic import Lock
    
    lock = Lock()
    start = time.monotonic()
    
    
    async def func():
        print(
            f"{time.monotonic() - start:.0f}:",
            f"thread={get_ident()}",
            f"task={anyio.get_current_task().id}",
            'start',
        )
        
        async with lock:
            await anyio.sleep(1)
        
        print(
            f"{time.monotonic() - start:.0f}:",
            f"thread={get_ident()}",
            f"task={anyio.get_current_task().id}",
            'stop',
        )
    
    
    async def main():
        async with anyio.create_task_group() as tasks:
            for _ in range(2):
                tasks.start_soon(func)
    
    
    for _ in range(2):
        Thread(target=anyio.run, args=[main]).start()

It prints something like this:

.. code-block::

    0: thread=140011620005632 task=140011624407888 start
    0: thread=140011611612928 task=140011602572720 start
    0: thread=140011620005632 task=140011624408560 start
    0: thread=140011611612928 task=140011602574512 start
    1: thread=140011620005632 task=140011624407888 stop
    2: thread=140011611612928 task=140011602572720 stop
    3: thread=140011620005632 task=140011624408560 stop
    4: thread=140011611612928 task=140011602574512 stop

As you can see, when using aiologic.Lock, tasks from different event loops have
an equal opportunity to acquire a lock. Using anyio.Lock would raise a
RuntimeError. And using threading.Lock would cause a deadlock.

Features
========

* Python 3.8+ support
* `CPython <https://www.python.org/>`_ and `PyPy <https://pypy.org/>`_ support
* Cancellation and timeouts support
* Optional `Trio-style checkpoints
  <https://trio.readthedocs.io/en/stable/reference-core.html#checkpoints>`_
* Only one checkpoint per asynchronous call
* Fairness wherever possible (with some caveats)
* Thread safety wherever possible

Synchronization primitives:

* Semaphores: counting and bounded
* Locks: primitive and reentrant
* Conditions
* Events: one-time and reusable
* Resource guards
* Queues: simple only

Supported concurrency libraries:

* `asyncio <https://docs.python.org/3/library/asyncio.html>`_
  and `trio <https://trio.readthedocs.io>`_ (coroutine-based)
* `eventlet <https://eventlet.readthedocs.io>`_
  and `gevent <https://www.gevent.org/>`_ (greenlet-based)

All synchronization primitives are implemented entirely on effectively atomic
operations, which gives incredible speedup on PyPy compared to alternatives
from the threading module. All this works thanks to GIL, but per-object locks
also ensure that `the same operations are still atomic
<https://peps.python.org/pep-0703/#container-thread-safety>`_, so aiologic also
works when running in a `free-threaded mode
<https://docs.python.org/3.13/whatsnew/3.13.html#free-threaded-cpython>`_.
