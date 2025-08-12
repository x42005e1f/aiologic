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

    async def work(i):
        print(f"worker #{i} started")
        await event  # waits one second
        print(f"worker #{i} notified")
        await event  # returns immediately
        print(f"worker #{i} stopped")

    async with anyio.create_task_group() as tg:
        tg.start_soon(work, 1)
        tg.start_soon(work, 2)

        await anyio.sleep(1)

        assert not event.is_set()
        event.set()  # notify all
        assert event.is_set()

.. tab:: green

  .. code:: python

    event = aiologic.Event()

    def work(i):
        print(f"worker #{i} started")
        event.wait()  # waits one second
        print(f"worker #{i} notified")
        event.wait()  # returns immediately
        print(f"worker #{i} stopped")

    with ThreadPoolExecutor(2) as executor:
        executor.submit(work, 1)
        executor.submit(work, 2)

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

    async def work(i):
        print(f"worker #{i} started")
        try:
            await anyio.sleep(i / 9)
        finally:
            event.down()  # one set
        print(f"worker #{i} stopped")

    async with anyio.create_task_group() as tg:
        for i in range(1, 10):
            event.up()  # one reset

            tg.start_soon(work, i)

        assert event.value == 9
        await event  # waits one second
        assert event.value == 0

.. tab:: green

  .. code:: python

    event = aiologic.CountdownEvent()

    def work(i):
        print(f"worker #{i} started")
        try:
            time.sleep(i / 9)
        finally:
            event.down()  # one set
        print(f"worker #{i} stopped")

    with ThreadPoolExecutor(9) as executor:
        for i in range(1, 10):
            event.up()  # one reset

            executor.submit(work, i)

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

Barriers
++++++++

:class:`aiologic.Latch` is an auto-signaling mechanism. It notifies all tasks
when they are all waiting, that is, call ``barrier.wait()`` /
``await barrier``. When the barrier is used, each wait call returns
immediately.

.. tab:: async

  .. code:: python

    barrier = aiologic.Latch(3)  # for three workers

    async def work(i):
        print(f"worker #{i} started")
        await barrier  # waits for all
        print(f"worker #{i} notified")
        await barrier  # returns immediately
        print(f"worker #{i} stopped")

    async with anyio.create_task_group() as tg:
        tg.start_soon(work, 1)
        tg.start_soon(work, 2)
        tg.start_soon(work, 3)

.. tab:: green

  .. code:: python

    barrier = aiologic.Latch(3)  # for three workers

    def work(i):
        print(f"worker #{i} started")
        barrier.wait()  # waits for all
        print(f"worker #{i} notified")
        barrier.wait()  # returns immediately
        print(f"worker #{i} stopped")

    with ThreadPoolExecutor(3) as executor:
        executor.submit(work, 1)
        executor.submit(work, 2)
        executor.submit(work, 3)

Unlike standard barriers (:class:`threading.Barrier` and
:class:`asyncio.Barrier`), :class:`aiologic.Latch` is a single-phase barrier
that cannot be reused. In this way it is similar to |cpp20-latch|_, and this is
why it is called a single-use barrier.

.. |cpp20-latch| replace:: ``std::latch`` from C++20
.. _cpp20-latch: https://en.cppreference.com/w/cpp/thread/latch.html

:class:`aiologic.Barrier`, in contrast, is a cyclic (or multi-phase) barrier.
It is convenient when your application logic contains sequential phases (as is
usually the case with parallel computing).

.. tab:: async

  .. code:: python

    barrier = aiologic.Barrier(2)  # for two workers

    async def work(i):
        print(f"worker #{i} started")
        await barrier  # waits for all
        print(f"worker #{i} notified")
        await barrier  # waits for all
        print(f"worker #{i} stopped")

    async with anyio.create_task_group() as tg:
        tg.start_soon(work, 1)
        tg.start_soon(work, 2)

.. tab:: green

  .. code:: python

    barrier = aiologic.Barrier(2)  # for two workers

    def work(i):
        print(f"worker #{i} started")
        barrier.wait()  # waits for all
        print(f"worker #{i} notified")
        barrier.wait()  # waits for all
        print(f"worker #{i} stopped")

    with ThreadPoolExecutor(2) as executor:
        executor.submit(work, 1)
        executor.submit(work, 2)

Nevertheless, :class:`aiologic.Barrier` is still not reusable. You cannot
return either of these two barrier types to the default, empty state, except
via ``barrier.wait()`` / ``await barrier`` (only for the cyclic barrier). If
you need the ``barrier.reset()`` method, there is a third type for that,
:class:`aiologic.RBarrier`.

Error handling
^^^^^^^^^^^^^^

Barriers require a special approach to error handling because of their
auto-signaling nature. If even one worker fails to wait, all others will wait
forever. To solve this problem, they have a special, "broken" state.

There are two ways to put a barrier into the broken state. The first is
automatic, on cancellation or timeouts. When ``barrier.wait()`` fails, each
current or future call raises :exc:`aiologic.BrokenBarrierError`. It is not
raised for the failed call if the failure is due to some other exception, but
it is raised on internal timeouts.

.. tab:: async

  .. code:: python

    barrier = aiologic.Latch(3)  # for three workers

    async def work(i):
        print(f"worker #{i} started")
        try:
            with anyio.fail_after(i):
                await barrier  # waits one second + fails
        except (aiologic.BrokenBarrierError, TimeoutError):
            print(f"worker #{i} failed")

    async with anyio.create_task_group() as tg:
        tg.start_soon(work, 1)
        tg.start_soon(work, 2)

.. tab:: green

  .. code:: python

    barrier = aiologic.Latch(3)  # for three workers

    def work(i):
        print(f"worker #{i} started")
        try:
            # with internal timeout
            barrier.wait(i)  # waits one second + fails
        except aiologic.BrokenBarrierError:
            print(f"worker #{i} failed")

    with ThreadPoolExecutor(2) as executor:
        executor.submit(work, 1)
        executor.submit(work, 2)

The second is manual, by calling ``barrier.abort()``. It is useful at startup
(when at least one worker fails to start), it is useful at shutdown, and it is
especially useful during phases.

.. tab:: async

  .. code:: python

    barrier = aiologic.Latch(1)  # for one worker

    try:
        pass  # do some work
    except:
        barrier.abort()  # something went wrong
        raise

    await barrier  # waits or fails

.. tab:: green

  .. code:: python

    barrier = aiologic.Latch(1)  # for one worker

    try:
        pass  # do some work
    except:
        barrier.abort()  # something went wrong
        raise

    barrier.wait()  # waits or fails

The case of sequential phases is particularly complex. Unless it is ensured
that no one raises an exception at a wait call on a successful wakeup, the
failed call must also abort the next phase. The need for correct handling
creates inconvenient patterns when using different barriers for different
phases:

.. tab:: async

  .. code:: python

    phase1 = aiologic.Latch(1)  # for one worker
    phase2 = aiologic.Latch(1)  # for one worker
    phase3 = aiologic.Latch(1)  # for one worker

    try:
        await phase1  # waits or fails

        pass  # do some work, phase #1
    except:
        phase2.abort()  # something went wrong
        raise

    try:
        await phase2  # waits or fails

        pass  # do some work, phase #2
    except:
        phase3.abort()  # something went wrong
        raise

.. tab:: green

  .. code:: python

    phase1 = aiologic.Latch(1)  # for one worker
    phase2 = aiologic.Latch(1)  # for one worker
    phase3 = aiologic.Latch(1)  # for one worker

    try:
        phase1.wait()  # waits or fails

        pass  # do some work, phase #1
    except:
        phase2.abort()  # something went wrong
        raise

    try:
        phase2.wait()  # waits or fails

        pass  # do some work, phase #2
    except:
        phase3.abort()  # something went wrong
        raise

This problem is solved by :class:`aiologic.Barrier` (and its relative
:class:`aiologic.RBarrier`). Besides the fact that using a single instance for
all phases simplifies the pattern to a single-phase case, it also supports use
as a context manager:

.. tab:: async

  .. code:: python

    barrier = aiologic.Barrier(1)  # for one worker

    async with barrier:  # waits or fails at enter
        pass  # do some work, phase #1

    async with barrier:  # waits or fails at enter
        pass  # do some work, phase #2

.. tab:: green

  .. code:: python

    barrier = aiologic.Barrier(1)  # for one worker

    with barrier:  # waits or fails at enter
        pass  # do some work, phase #1

    with barrier:  # waits or fails at enter
        pass  # do some work, phase #2

.. note::

    Using aiologic barriers as context managers ensures that
    ``barrier.abort()`` is called if an exception has been raised. However,
    :class:`asyncio.Barrier` instances do not do this, and do not even put a
    barrier into the broken state on exceptions raised at ``await
    barrier.wait()``. In fact, the only way to put an asyncio barrier into the
    broken state is to explicitly do ``await barrier.abort()``.

    The possible reason for such behavior in asyncio is quite simple. Like any
    other modern asynchronous framework, asyncio has developed cancellation
    semantics. Instead of doing ``await barrier.abort()``, you can simply
    cancel tasks directly. Or even use :class:`asyncio.TaskGroup`. This
    eliminates the need to mess with :exc:`asyncio.BrokenBarrierError` at all.

    What makes aiologic different is that its barriers can work with different
    libraries at the same time, and each may have different cancellation
    semantics (or even no cancellation semantics). So you need to work with
    :exc:`aiologic.BrokenBarrierError` on all interfaces.

Finalizing
^^^^^^^^^^

:class:`aiologic.Barrier` (and its relative :class:`aiologic.RBarrier`) gives
each worker its own integer, in wakeup order. It is returned both when waiting
and when using a barrier as a context manager.

.. tab:: async

  .. code:: python

    barrier = aiologic.Barrier(3)  # for three workers

    async def work(i):
        print(f"worker #{i} started")
        async with barrier as j:  # int in range(0, 3)
            print(f"worker #{i} notified as #{j + 1}")
        print(f"worker #{i} stopped")

    async with anyio.create_task_group() as tg:
        tg.start_soon(work, 1)
        tg.start_soon(work, 2)
        tg.start_soon(work, 3)

.. tab:: green

  .. code:: python

    barrier = aiologic.Barrier(3)  # for three workers

    def work(i):
        print(f"worker #{i} started")
        with barrier as j:  # int in range(0, 3)
            print(f"worker #{i} notified as #{j + 1}")
        print(f"worker #{i} stopped")

    with ThreadPoolExecutor(3) as executor:
        executor.submit(work, 1)
        executor.submit(work, 2)
        executor.submit(work, 3)

This can be used to finalize a resource in a single thread when the previous
phase is complete.

Special behavior
^^^^^^^^^^^^^^^^

The barriers implement the same special behavior as :class:`aiologic.Event`,
but with the following specifics:

1. Successful and unsuccessful wakeups (due to explicit or implicit
   ``barrier.abort()``) can race. When threads wake up in a natural way (due to
   sufficient ``barrier.wait()`` calls), they wake each other up with the
   information that the wakeup was successful. When threads wake up in an
   unnatural way (due to a timeout, an exception, or a ``barrier.abort()``
   call), they do the same thing, but with the information that the wakeup was
   unsuccessful. In a multithreaded scenario where both types of wakeup
   coexist, the success of a thread's wakeup is determined by the race
   condition.
2. The parallelism of successful wakeup is limited for
   :class:`aiologic.Barrier` and :class:`aiologic.RBarrier`. When tasks are
   more than expected, they are divided into phases. Tasks wake up each other
   in their phase, but the wakeup of phases is sequential - a task from the
   next phase will be woken up only when the wakeup initiator wakes up all
   tasks in its phase. In particular, the case where the expected number is
   :math:`1` and the actual number is :math:`n` gives :math:`O(n^2)` complexity
   of a full wakeup (instead of :math:`O(n)` if the expected number was
   :math:`n`).
3. The wakeup order of phases may not be exactly FIFO for
   :class:`aiologic.Barrier` and :class:`aiologic.RBarrier` without GIL (free
   threading, perfect fairness disabled). When perfect fairness is disabled, a
   separate list is used to parallelize wakeups. As a result, an unsuccessful
   wakeup may wake up new tasks before the phase wakeup is complete.

The ability of the barriers to wake up all tasks at once opens the way for one
non-trivial application of them: solving the squares problem. By using a
barrier to synchronize the start of threads, you can ensure that none of them
run until they all start, and thus eliminate unnecessary context switching (and
wasted CPU cycles) during the wakeup process. As a result, you will lower the
time complexity of a full start from :math:`O(n^2)` to :math:`O(n)`. This
extends the already known use of barriers for similar purposes, such as
reducing the impact of startup overhead for timeouts (improving test
reproducibility).

.. code:: python

    import threading
    import time

    import aiologic

    N = 1000

    barrier = aiologic.Latch(N)
    stopped = False


    def work(i):
        global stopped

        # with:     0.27 seconds
        # without: 12.95 seconds
        barrier.wait()

        if i == N - 1:  # the last thread
            stopped = True  # stop the work

        while not stopped:
            time.sleep(0)  # do some work


    for i in range(N):
        threading.Thread(target=work, args=[i]).start()

Like all other aiologic primitives, the barriers implement the FIFO wakeup
order. This is achieved by forcing a checkpoint for the task that came last in
the current phase. Besides giving more expected and predictable behavior, this
also distinguishes them from :class:`asyncio.Barrier`.

.. tab:: aiologic.Barrier

  .. code:: python

    import asyncio

    from itertools import count

    import aiologic


    async def work(barrier, c, i):
        print(f"worker #{i} started")
        async with barrier:
            j = next(c)
            print(f"worker #{i} notified as #{j}")
            assert j == i  # passes for all tasks
        print(f"worker #{i} stopped")


    async def main():
        barrier = aiologic.Barrier(3)  # for three workers
        c = count(1)  # for wakeup enumerating

        async with asyncio.TaskGroup() as tg:
            tg.create_task(work(barrier, c, 1))
            tg.create_task(work(barrier, c, 2))
            tg.create_task(work(barrier, c, 3))


    asyncio.run(main())

.. tab:: asyncio.Barrier

  .. code:: python

    import asyncio

    from itertools import count

    # import aiologic


    async def work(barrier, c, i):
        print(f"worker #{i} started")
        async with barrier:
            j = next(c)
            print(f"worker #{i} notified as #{j}")
            assert j == i  # fails for all tasks
        print(f"worker #{i} stopped")


    async def main():
        barrier = asyncio.Barrier(3)  # for three workers
        c = count(1)  # for wakeup enumerating

        async with asyncio.TaskGroup() as tg:
            tg.create_task(work(barrier, c, 1))
            tg.create_task(work(barrier, c, 2))
            tg.create_task(work(barrier, c, 3))


    asyncio.run(main())
