..
  SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
  SPDX-License-Identifier: CC-BY-4.0

Cheatsheet
==========

Since the documentation is currently still under development, here is a concise
set of notes on the main features of aiologic. It is intended to be transformed
into separate sections in the future.

.. note::

    All information presented here and in general in all documentation is
    relevant for the latest (development) version. Make sure you install the
    package from GitHub before we start.

Cancellation and timeouts
-------------------------

"When in Rome, do as the Romans do" is a proverb attributed to St. Ambrose, a
fourth-century bishop of Milan, and it also reflects well aiologic's vision of
cancellation and timeouts. You can pass timeouts when using "green" libraries,
but when using "async" libraries you have to use the mechanisms they provide.

.. tab:: async

  .. code:: python

    async with aiologic.Condition() as cv:
        await asyncio.wait_for(cv, timeout=5)

.. tab:: green

  .. code:: python

    with aiologic.Condition() as cv:
        cv.wait(timeout=5)

One reason why aiologic does not provide its own timeouts for async libraries
is `the difference between cancellation semantics <https://
anyio.readthedocs.io/en/stable/cancellation.html
#differences-between-asyncio-and-anyio-cancellation-semantics>`_ combined with
the fact that AnyIO with the asyncio backend cannot be distinguished from pure
asyncio on the aiologic side.

Synchronization primitives
--------------------------

Synchronization primitives are used to organize controlled interactions between
tasks. It can be simple notification, mutual exclusion, or any other effect the
programmer wants.

Events
++++++

:class:`aiologic.Event` is one of the simplest signaling mechanisms. You can
use it to notify other tasks that a particular condition has become true, such
as a shutdown. When the event is set, each wait call returns immediately.

.. tab:: async

  .. code:: python

    event = aiologic.Event()

    async def worker(i):
        print(f"worker #{i} started")
        await event  # waits one second
        print(f"worker #{i} notified")
        await event  # returns immediately
        print(f"worker #{i} stopped")

    async with anyio.create_task_group() as tg:
        tg.start_soon(worker, 1)
        tg.start_soon(worker, 2)

        await anyio.sleep(1)

        assert not event.is_set()
        event.set()  # notify all
        assert event.is_set()

.. tab:: green

  .. code:: python

    event = aiologic.Event()

    def worker(i):
        print(f"worker #{i} started")
        event.wait()  # waits one second
        print(f"worker #{i} notified")
        event.wait()  # returns immediately
        print(f"worker #{i} stopped")

    with ThreadPoolExecutor(2) as executor:
        executor.submit(worker, 1)
        executor.submit(worker, 2)

        time.sleep(1)

        assert not event.is_set()
        event.set()  # notify all
        assert event.is_set()

Unlike standard events (:class:`threading.Event` and :class:`asyncio.Event`),
:class:`aiologic.Event` cannot be reset to its initial state. In this way it is
similar to AnyIO / Trio events, and this is why it is called a one-time event.

:class:`aiologic.REvent`, in contrast, is a reusable event. It achieves this at
the cost of some performance degradation, so it is recommended for use only
when really needed.

.. code:: python

    event = aiologic.REvent()

    assert not event.is_set()
    event.set()  # notify all
    assert event.is_set()
    event.clear()  # reset
    assert not event.is_set()

.. note::

    Repeated calls to ``event.set()`` / ``event.clear()`` when the event is
    already set / unset have no effect. This corresponds to the behavior of the
    standard events, but may be unexpected if you have not worked with them
    before.

:class:`aiologic.CountdownEvent` represents a completely different class of
events that is inspired by |dotnet-countdownevent|_. Unlike regular events, it
counts the number of "sets" and "resets" (to wake up tasks, you need to "set" a
countdown event as many times as it has been "reset"), and it is "set" by
default.

.. |dotnet-countdownevent| replace:: ``CountdownEvent`` from .NET Framework 4.0
.. _dotnet-countdownevent: https://learn.microsoft.com/en-us/dotnet/api/
   system.threading.countdownevent?view=netframework-4.0

.. tab:: async

  .. code:: python

    event = aiologic.CountdownEvent()

    async def worker(i):
        print(f"worker #{i} started")
        try:
            await anyio.sleep(i / 9)
        finally:
            event.down()  # one set
        print(f"worker #{i} stopped")

    async with anyio.create_task_group() as tg:
        for i in range(1, 10):
            event.up()  # one reset

            tg.start_soon(worker, i)

        assert event.value == 9
        await event  # waits one second
        assert event.value == 0

.. tab:: green

  .. code:: python

    event = aiologic.CountdownEvent()

    def worker(i):
        print(f"worker #{i} started")
        try:
            time.sleep(i / 9)
        finally:
            event.down()  # one set
        print(f"worker #{i} stopped")

    with ThreadPoolExecutor(9) as executor:
        for i in range(1, 10):
            event.up()  # one reset

            executor.submit(worker, i)

        assert event.value == 9
        event.wait()  # waits one second
        assert event.value == 0

It is useful for signaling when some group of events has occurred, such as all
threads, tasks, or whatever else has finished. And compared to standard
functions such as :func:`concurrent.futures.wait` or :func:`asyncio.gather`, it
has four key advantages:

1. It supports adding new tasks to wait dynamically, just by calling
   ``event.up()``, which works even from another thread. The standard functions
   work only with a fixed set.
2. It can be used with any library, with any number of waiting tasks, and with
   any worker tasks of any nature, which only requires calling ``event.down()``
   when a single unit completes. The standard functions do not have such
   versatility.
3. It can be reset to its initial (set) state at any time externally by calling
   ``event.clear()``. The standard functions require more sophisticated
   techniques.
4. With :math:`m` waiting tasks for the same group of :math:`n` worker tasks,
   the time complexity of the entire "join" operation will be only
   :math:`O(m+n)`. The standard functions, in contrast, give :math:`O(mn)` time
   complexity because they require adding a callback to each unit (and this is
   the same time complexity as if each waiting task were to loop through each
   worker task to wait one by one).

Thus, countdown events are a convenient way to implement joining. But their
disadvantage is that they require :math:`O(n)` memory, where :math:`n` is their
current counter.

Special behavior
^^^^^^^^^^^^^^^^

The use of atomic operations as well as the lock-free implementation style
gives aiologic primitives a special behavior. And first of all it concerns
atomicity of primitives' methods, such as ``event.set()``.

When you call :meth:`threading.Event.set`, it works in mutual exclusion mode -
in fact, :class:`threading.Event` is built on top of
:class:`threading.Condition` (see source code). But :meth:`aiologic.Event.set`
has a different situation - it allows its parallel execution in different
threads, which affects the wakeup order and when the method completes its
execution. So all aiologic primitives have to use some tricks to provide
predictable behavior and emulate atomicity (within some limits).

The events implement the following special behavior:

1. The wakeup order is exactly FIFO for all events except
   :class:`aiologic.Event` without GIL (free threading, perfect fairness
   disabled). The latter allows racing between threads, which makes the order
   non-deterministic - your async tasks may wake up in a different order than
   when they called ``await event``. If you need determinism in free threading,
   you can enable perfect fairness via the ``AIOLOGIC_PERFECT_FAIRNESS``
   environment variable, but this will cost you some (noticeable) performance
   degradation with a huge number of threads.
2. All tasks wake up at the same time (or in several scheduler passes, usually
   one or two, if perfect fairness is disabled), which gives :math:`O(n)` time
   complexity of a full wakeup. That is, both when returning from the
   ``event.set()`` method and when returning from the ``event.wait()`` method,
   you can expect that all tasks are already scheduled for execution, which is
   especially useful for benchmarks. This is different from the threading
   events, which due to mutual exclusion give :math:`O(n^2)` time complexity of
   a full wakeup.
3. The ``event.set()`` call wakes up only those tasks that were waiting until
   the nearest reset and until the first task wakes up, for which markers and
   timestamps are used. At the same time, the woken task inherits the deadline
   (current timestamp) of the one that woke it up to wake up its neighbors.
   This ensures that the ``event.clear()`` + ``event.wait()`` combination is
   processed correctly after wakeup (otherwise ``event.wait()`` could return
   immediately), and that the wakeup is done in a finite amount of time, which
   eliminates possible resource starvation.
4. When no wakeup/waiting is required, the event methods work as truly
   non-blocking, which gives good scalability. In particular, the
   ``event.up()`` method always runs for :math:`O(1)`, and the ``event.down()``
   method runs for :math:`O(1)` until the counter goes to zero. This is
   different from the threading events, which, for example, may take
   :math:`O(n)` time for repeated ``event.set()`` calls due to mutual
   exclusion.

You can read about the origins of time complexity in mutual exclusion in `the
one issue comment <https://github.com/apache/airflow/issues/50185
#issuecomment-2928285691>`_. While the example of waking up all threads is
considered there, the same inferences can be applied to waking up on a mutex.
