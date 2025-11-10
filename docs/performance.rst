..
  SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
  SPDX-License-Identifier: CC-BY-4.0

Performance
===========

You probably came here to see how fast aiologic is. To see detailed
measurements, beautifully drawn with `Matplotlib <https://matplotlib.org/>`__,
such as in `the reply to one issue <https://github.com/x42005e1f/aiologic/
issues/7#issuecomment-3067270072>`__. Well, try to come back another time!

The purpose of this section is to show how deep the rabbit hole in which
aiologic has burrowed goes. Just as with great power comes great
responsibility, with great opportunity comes great challenges that you are not
aware of.

A world full of squares
-----------------------

When working with threading, programmers usually do not think about how
everything works under the hood. They rely on the OS-level scheduler to create
good visibility of parallel execution and treat it as a black box. But
abstractions leak when it comes to the execution time of your code.

Meet the square
+++++++++++++++

Suppose we want to start :math:`n` threads to perform some long work. Whether
it is for parallel computing with `NumPy <https://numpy.org/>`__ arrays, for
network operations, or for simulating some game processes - it does not matter.
Here is an example that allows us to estimate the time spent on performing a
full start of all threads:

.. code:: python

    #!/usr/bin/env python3

    import sys
    import threading
    import time


    def main():
        n = int(sys.argv[1])  # the number of threads
        count = [None] * n  # as a thread-safe counter

        def work():
            count.pop()  # decrement

            while count:  # wait for the other threads
                time.sleep(0)  # do some work

        threads = [threading.Thread(target=work) for _ in range(n)]
        start_time = time.perf_counter()

        for thread in threads:  # start all threads
            thread.start()

        for thread in threads:  # join all threads
            thread.join()

        print(time.perf_counter() - start_time)  # elapsed time in seconds


    if __name__ == "__main__":
        sys.exit(main())

.. tab:: CPython

  .. table::
    :class: widetable

    +-------------+------------------------+--------------------+
    | n (threads) | elapsed time (seconds) |       factor       |
    +=============+========================+====================+
    |     100     |   00.128054202999920   | 01.000000000000000 |
    +-------------+------------------------+--------------------+
    |     200     |   00.523237066998263   | 04.086059299424878 |
    +-------------+------------------------+--------------------+
    |     300     |   01.185488475995953   | 09.257708440828740 |
    +-------------+------------------------+--------------------+
    |     400     |   02.170950671992614   | 16.953373033714293 |
    +-------------+------------------------+--------------------+
    |     500     |   03.374565812002402   | 26.352636094299218 |
    +-------------+------------------------+--------------------+
    |     600     |   04.908995083998889   | 38.335290595670400 |
    +-------------+------------------------+--------------------+
    |     700     |   06.699139770003967   | 52.314876146690560 |
    +-------------+------------------------+--------------------+
    |     800     |   08.542142848004005   | 66.707243088376910 |
    +-------------+------------------------+--------------------+
    |     900     |   10.993017560002045   | 85.846597007120040 |
    +-------------+------------------------+--------------------+

.. tab:: PyPy

  .. table::
    :class: widetable

    +-------------+------------------------+--------------------+
    | n (threads) | elapsed time (seconds) |       factor       |
    +=============+========================+====================+
    |     100     |   00.636086261991295   | 01.000000000000000 |
    +-------------+------------------------+--------------------+
    |     200     |   02.507049866995658   | 03.941367730765371 |
    +-------------+------------------------+--------------------+
    |     300     |   05.806155779995606   | 09.127937713698122 |
    +-------------+------------------------+--------------------+
    |     400     |   10.474476018003770   | 16.467068452654484 |
    +-------------+------------------------+--------------------+
    |     500     |   16.528380447998643   | 25.984495241660852 |
    +-------------+------------------------+--------------------+
    |     600     |   23.248486744996626   | 36.549267189352980 |
    +-------------+------------------------+--------------------+
    |     700     |   33.561982030005310   | 52.763255607719150 |
    +-------------+------------------------+--------------------+
    |     800     |   41.350978271002530   | 65.008444203073240 |
    +-------------+------------------------+--------------------+
    |     900     |   53.098309983994110   | 83.476586678303040 |
    +-------------+------------------------+--------------------+

In this example, we take the first command-line argument as :math:`n`. We start
the threads, and each one performs its work (emulates system calls) until all
of them are started, which we control using the list as a thread-safe counter.

.. note::

    You can replace ``time.sleep(0)`` with ``pass`` to emulate CPU load, but
    this is not recommended. In this case, the thread will not yield control
    until it has spent its timeslice (5 milliseconds by default; you can change
    it via :func:`sys.setswitchinterval`). This will result in seconds of real
    time even with a small number of threads, with a large spread, which is not
    suitable for estimation.

    Either way, system call emulation gives the same interpretation as you can
    get with CPU load.

Below the code, you can see the measurements. They were taken on a laptop
running Linux with a dual-core processor. One minute was allocated for each
:math:`n` (the code was run multiple times within one minute), and the median
was taken as the final time.

Let us interpret the results. Increasing the number of threads by :math:`k`
times increases the time of a full start by :math:`k^2` times: 100 → 200 gives
a factor of 4 (:math:`=2^2`), 100 → 300 gives a factor of 9 (:math:`=3^2`), and
so on. Thus, we can clearly see that the dependence of the time of a full start
on the number of threads is not linear — in fact, it is quadratic. But why does
this happen?

When you start a thread in Python, two operations are performed under the hood:

1. The interpreter asks the operating system to start the thread (see the
   :mod:`_thread` module).
2. The implementation of :meth:`threading.Thread.start` waits for the thread to
   notify that it has started.

Thus, calling :meth:`threading.Thread.start` effectively forces the main thread
in our example to do a context switch (since it must be notified by the
thread). And since the operating system needs to emulate the concurrent
execution of all threads, the whole thing does not look like ping-pong between
the main thread and the newly started thread - the operating system also needs
to allocate CPU resources to the already running threads.

If we look at the order in which context switching occurs on each pass of the
scheduler, we will see something like this (where thread #0 is the main
thread):

* ``±thread #0`` (starting the first thread)
* ``+thread #1`` (running one thread)
* ``±thread #0 → thread #1`` (starting the second thread)
* ``+thread #2 → thread #1`` (running two threads)
* ``±thread #0 → thread #2 → thread #1`` (starting the third thread)
* ``+thread #3 → thread #2 → thread #1`` (running three threads)
* ...
* ``±thread #0 → thread #(N-1) → ... → thread #1`` (starting the last thread)
* ``±thread #(N) → -thread #(N-1) → ... → -thread #1`` (stopping all threads)
* ``±thread #0`` (the end)

In particular, for :math:`n=1`:

* ``±thread #0`` (starting the first/last thread)
* ``±thread #1`` (stopping all threads)
* ``±thread #0`` (the end)

For :math:`n=3`:

* ``±thread #0`` (starting the first thread)
* ``+thread #1`` (running one thread)
* ``±thread #0 → thread #1`` (starting the second thread)
* ``+thread #2 → thread #1`` (running two threads)
* ``±thread #0 → thread #2 → thread #1`` (starting the third thread)
* ``±thread #3 → -thread #2 → -thread #1`` (stopping all threads)
* ``±thread #0`` (the end)

With each new thread, the required number of context switches to start the next
one increases. We see two triangles (:math:`1+1+2+2+3+3+…+n+n`
:math:`=2(1+2+3+…+n)` context switches until the end), which become one
*square* when the constants is discarded (:math:`2(1+2+3+…+n)+1`
:math:`=2\frac{n(1+n)}{2}+1` :math:`=n(1+n)+1` :math:`⇒n(n)` :math:`=n^2`) -
that is where the quadratic `time complexity <https://en.wikipedia.org/wiki/
Time_complexity>`__ comes from!

Our example is not the only one with the square. There are others, also scarily
simple and reproducible. But let us now express the time complexity using `big
O notation <https://en.wikipedia.org/wiki/Big_O_notation>`__ for simplicity.
From this point on, "square" and :math:`O(n^2)` are synonymous.

Squares, squares everywhere
+++++++++++++++++++++++++++

Suppose we use mutual exclusion to provide exclusive access to a shared state.
We have :math:`n` threads that first synchronize via a lock, aka a mutex, and
then do some work until each thread gains access to the shared state. And by
some coincidence, each thread (except the first one) waited on the lock.

.. code:: python

    #!/usr/bin/env python3

    import sys
    import threading
    import time


    def main():
        n = int(sys.argv[1])  # the number of threads
        count = []  # as a thread-safe counter
        start_time = None
        lock = threading.Lock()

        def work():
            nonlocal start_time

            count.append(None)  # increment

            with lock:
                if start_time is None:  # the first thread
                    while len(count) < n:  # wait for the other threads
                        time.sleep(0)  # (via polling)

                    start_time = time.perf_counter()

            count.pop()  # decrement

            while count:  # wait for the other threads
                time.sleep(0)  # do some work

        threads = [threading.Thread(target=work) for _ in range(n)]

        for thread in threads:  # start all threads
            thread.start()

        for thread in threads:  # join all threads
            thread.join()

        print(time.perf_counter() - start_time)  # elapsed time in seconds


    if __name__ == "__main__":
        sys.exit(main())

.. tab:: CPython

  .. table::
    :class: widetable

    +-------------+------------------------+--------------------+
    | n (threads) | elapsed time (seconds) |       factor       |
    +=============+========================+====================+
    |     100     |   00.040662774990778   | 01.000000000000000 |
    +-------------+------------------------+--------------------+
    |     200     |   00.163145697966684   | 04.012163409990640 |
    +-------------+------------------------+--------------------+
    |     300     |   00.384463688998949   | 09.454929947258597 |
    +-------------+------------------------+--------------------+
    |     400     |   00.717438969993964   | 17.643630326672640 |
    +-------------+------------------------+--------------------+
    |     500     |   01.193486175034195   | 29.350829482367010 |
    +-------------+------------------------+--------------------+
    |     600     |   01.716789263999090   | 42.220169783995960 |
    +-------------+------------------------+--------------------+
    |     700     |   02.327792735013645   | 57.246283253947780 |
    +-------------+------------------------+--------------------+
    |     800     |   02.976299398986157   | 73.194694647896710 |
    +-------------+------------------------+--------------------+
    |     900     |   03.700176201004069   | 90.996647470400200 |
    +-------------+------------------------+--------------------+

.. tab:: PyPy

  .. table::
    :class: widetable

    +-------------+------------------------+--------------------+
    | n (threads) | elapsed time (seconds) |       factor       |
    +=============+========================+====================+
    |     100     |   00.238932970969472   | 01.000000000000000 |
    +-------------+------------------------+--------------------+
    |     200     |   00.900706941029057   | 03.769705526091408 |
    +-------------+------------------------+--------------------+
    |     300     |   02.093295602011494   | 08.761016085465032 |
    +-------------+------------------------+--------------------+
    |     400     |   03.856209805991966   | 16.139295428108436 |
    +-------------+------------------------+--------------------+
    |     500     |   06.133253426000010   | 25.669347353420060 |
    +-------------+------------------------+--------------------+
    |     600     |   08.936387986002956   | 37.401234119106725 |
    +-------------+------------------------+--------------------+
    |     700     |   12.695628314977512   | 53.134685696431590 |
    +-------------+------------------------+--------------------+
    |     800     |   16.309672918985598   | 68.260453351452480 |
    +-------------+------------------------+--------------------+
    |     900     |   20.873524700989947   | 87.361424487777820 |
    +-------------+------------------------+--------------------+

.. note::

    The code above does not guarantee that all threads will actually be in the
    lock's waiting queue. In fact, a thread may do a context switch after the
    increment but before attempting to acquire the lock. However, it is
    extremely unlikely that it will not have time to join the waiting queue, so
    this fact does not affect the results.

    It is possible to provide such a guarantee using one of the aiologic
    primitives and their :attr:`~aiologic.Lock.waiting` property, but this
    approach would not inspire the same trust as using standard primitives,
    would it?

Well, :math:`O(n^2)` again! And this is quite expected.

On each pass of the scheduler, one :meth:`~threading.Lock.release` call is
made. This means that on the next pass, the number of running threads will be
increased by one. The remaining threads cannot wake up until future passes, as
they are still queued. And at the same time, the operating system still
allocates CPU resources to the running threads.

* ...
* ``+thread #1`` (running one thread)
* ``+thread #2 → thread #1`` (running two threads)
* ``+thread #3 → thread #2 → thread #1`` (running three threads)
* ...
* ``±thread #(N) → -thread #(N-1) → ... → -thread #1`` (stopping all threads)
* ...

In particular, for :math:`n=1`:

* ...
* ``±thread #1`` (stopping all threads)
* ...

For :math:`n=3`:

* ...
* ``+thread #1`` (running one thread)
* ``+thread #2 → thread #1`` (running two threads)
* ``±thread #3 → -thread #2 → -thread #1`` (stopping all threads)
* ...

This is a very obvious triangle, which becomes half of one square, and
therefore gives :math:`O(n^2)`: :math:`1+2+3+…+n` :math:`=\frac{n(1+n)}{2}`
:math:`⇒n(n)` :math:`=n^2`.

Okay, we have examined two simple but important examples. It will now become
clear why.

In both cases, we observed that increasing the number of threads increased the
time spent quadratically. When you meet the square, your code will run about as
long with 1,000 threads as it would with 1,000,000 threads! And since the
square is explained by the principles of the OS-level scheduler, the problem is
actually fundamental, and you can find squares when working with any
multithreaded code in any programming language. So let us call it *the square
problem*.

In the first case, we addressed the topic of starting multiple threads. Despite
its simplicity, its interpretation also applies to other similar, more general
cases, related to waking up multiple threads. For example, such as multiple
:meth:`condition.notify() <threading.Condition.notify>`,
:meth:`semaphore.release() <threading.Semaphore.release>`, or even just
:meth:`lock.release() <threading.Lock.release>`! Waiting for one queue by
multiple threads also suffers from the square problem. We will give all such
cases one concise name - *the notify case*.

In the second case, we addressed the topic of mutual exclusion, and we will
refer to all related cases simply as *the mutex case*. You know how ubiquitous
mutual exclusion is; you can encounter it in almost any multithreaded
application. Moreover, all standard threading primitives are implemented using
:class:`threading.Lock`, which spreads the problem to all classic multithreaded
applications! The world you know is poisoned by a dark army of
squares...

But how close are we to the truth?

The square is (not) a lie
+++++++++++++++++++++++++

All our calculations would hardly have any practical value if the square
problem did not affect the real world. Therefore, we need to understand how
serious it is and whether it can exist outside laboratory conditions.

First, the square problem only exists in cases where we have threads that run
for a sufficiently long time. If the threads fall asleep (or stop altogether)
shortly after waking up, they will not consume CPU resources, since their
execution will not be rescheduled, resulting in :math:`O(n)` instead of
:math:`O(n^2)`.

Second, the notify case is only affected by the square problem when waking up
one thread requires (or is likely to cause) a context switch. In particular,
waking up threads using primitives from the :mod:`threading` module is just
:meth:`lock.release() <threading.Lock.release>` under the hood, and it is
usually called without a context switch. This results in amortized
:math:`O(n)`, since one timeslice allows so many operations to be performed
before the scheduler forcibly preempts the thread that, on average, the square
is not observed.

.. code:: python

    #!/usr/bin/env python3

    import sys
    import threading
    import time


    def main():
        n = int(sys.argv[1])  # the number of threads
        count = [None] * (n - 1)  # as a thread-safe counter
        start_time = None
        sem = threading.Semaphore(0)

        def work():
            nonlocal start_time

            try:
                count.pop()  # decrement
            except IndexError:  # the last thread
                start_time = time.perf_counter()

                for _ in range(n - 1):  # wake up the other threads
                    sem.release()  # wake up one thread
            else:
                sem.acquire()  # wait for the last thread

            count.append(None)  # increment

            while len(count) < n:  # wait for the other threads
                time.sleep(0)  # do some work

        threads = [threading.Thread(target=work) for _ in range(n)]

        for thread in threads:  # start all threads
            thread.start()

        for thread in threads:  # join all threads
            thread.join()

        print(time.perf_counter() - start_time)  # elapsed time in seconds


    if __name__ == "__main__":
        sys.exit(main())

.. tab:: CPython

  .. table::
    :class: widetable

    +-------------+------------------------+--------------------+
    | n (threads) | elapsed time (seconds) |       factor       |
    +=============+========================+====================+
    |     100     |   00.006712578702718   | 01.000000000000000 |
    +-------------+------------------------+--------------------+
    |     200     |   00.014982033986598   | 02.231934201461476 |
    +-------------+------------------------+--------------------+
    |     300     |   00.024709819816053   | 03.681121802869522 |
    +-------------+------------------------+--------------------+
    |     400     |   00.035512225236744   | 05.290399831344142 |
    +-------------+------------------------+--------------------+
    |     500     |   00.047473615966737   | 07.072336589143383 |
    +-------------+------------------------+--------------------+
    |     600     |   00.062206360045820   | 09.267133064768720 |
    +-------------+------------------------+--------------------+
    |     700     |   00.089063511230052   | 13.268151506959379 |
    +-------------+------------------------+--------------------+
    |     800     |   00.114488433580846   | 17.055805026835300 |
    +-------------+------------------------+--------------------+
    |     900     |   00.145504496991634   | 21.676393445147617 |
    +-------------+------------------------+--------------------+

.. tab:: PyPy

  .. table::
    :class: widetable

    +-------------+------------------------+--------------------+
    | n (threads) | elapsed time (seconds) |       factor       |
    +=============+========================+====================+
    |     100     |   00.413370564114302   | 01.000000000000000 |
    +-------------+------------------------+--------------------+
    |     200     |   01.585753257852048   | 03.836154277820242 |
    +-------------+------------------------+--------------------+
    |     300     |   03.530520770698786   | 08.540813200531982 |
    +-------------+------------------------+--------------------+
    |     400     |   06.261200568173081   | 15.146701559624784 |
    +-------------+------------------------+--------------------+
    |     500     |   09.606545099988580   | 23.239548080961672 |
    +-------------+------------------------+--------------------+
    |     600     |   13.984252063091844   | 33.829820691405146 |
    +-------------+------------------------+--------------------+
    |     700     |   19.215607445687056   | 46.485185723997720 |
    +-------------+------------------------+--------------------+
    |     800     |   25.340027304831892   | 61.300996018248270 |
    +-------------+------------------------+--------------------+
    |     900     |   31.295299415010960   | 75.707614745295200 |
    +-------------+------------------------+--------------------+

Oops, we got some interesting results! On CPython, we see something close to
:math:`O(n^2)` divided by four, and on PyPy, it is clearly :math:`O(n^2)`. But
why?

If we look at the internal structure of the semaphore, it is implemented quite
simply: :class:`threading.Condition` is used to synchronize the internal state
and to control the threads' wake-up.

:meth:`sem.acquire() <threading.Semaphore.acquire>` (simplified
interpretation):

1. Acquire the underlying lock.
2. Join the condition's waiting queue.
3. Release the underlying lock.
4. Wait to be notified.
5. Acquire the underlying lock.
6. Release the underlying lock.

:meth:`sem.release() <threading.Semaphore.release>` (simplified
interpretation):

1. Acquire the underlying lock.
2. Notify the first waiting thread.
3. Release the underlying lock.

We will refer to their operations as a-i and r-j, respectively. So now let us
consider possible scenarios, identifying a-i with consumers and r-j with a
producer.

1. Let us suppose that context switching between r-1 and r-3 has occurred, and
   none of :math:`n` consumers has called :meth:`sem.acquire()
   <threading.Semaphore.acquire>` yet. Then, being scheduled for execution,
   they will all, with a fairly high probability, join the lock's waiting queue
   at a-1. Execution will switch to the producer, it will release the lock at
   r-3, but will fall asleep at r-1 due to the waiting queue order. Next, each
   consumer will continue its execution and, with a fairly high probability,
   will fall asleep at a-4, which gives us too short an execution time, meaning
   :math:`O(n)`.
2. Let us suppose that context switching between r-1 and r-3 has occurred, and
   :math:`k` consumers are waiting at a-4. Then, being scheduled for execution,
   they will all, with a fairly high probability, join the lock's waiting queue
   at a-5. Execution will switch to the producer, it will release the lock at
   r-3, but will fall asleep at r-1 due to the waiting queue order. Next, each
   consumer will continue its execution and, with a fairly high probability,
   will complete the :meth:`sem.acquire() <threading.Semaphore.acquire>` call,
   which gives us arbitrarily long execution time, meaning :math:`O(k^2)`.
3. Let us suppose that the producer has finished its work, but at some point
   context switching between a-5 and a-6 has occurred, and :math:`k` consumers
   are waiting at a-4. Then, being scheduled for execution, they will all, with
   a fairly high probability, join the lock's waiting queue at a-5. Obviously,
   this is again :math:`O(k^2)`.

These three scenarios are simple, but they have interesting consequences:

1. If one :meth:`sem.release() <threading.Semaphore.release>` call is
   interrupted, this gives :math:`O((k+m)^2-m^2)` :math:`=O(k^2+nm+m^2-m^2)`
   :math:`=O(k^2+km)` :math:`≈O(n^2)`, where :math:`n` is the number of all
   threads considered, :math:`k` is the number of waiting threads, and
   :math:`m` is the number of threads that have already completed the
   :meth:`sem.acquire() <threading.Semaphore.acquire>` call.
2. If not all of the threads have started the :meth:`sem.acquire()
   <threading.Semaphore.acquire>` call, this leads to the :math:`k` increasing,
   and consequently to the square growing.
3. The previous two points also apply to context switching between a-5 and a-6,
   and therefore to the entire mutex case.

Well, we have discovered a terrifying truth! Despite the seemingly low
probability, just one context switch is enough to give us :math:`O(n^2)`.
Moreover, the longer the lock is held, the higher the probability of
:math:`O(n^2)` due to preemptive context switching.

Scenarios involving multiple wake-ups per call, such as
:meth:`semaphore.release(n) <threading.Semaphore.release>`, :meth:`event.set()
<threading.Event.set>`, and even :meth:`barrier.wait()
<threading.Barrier.wait>`, do not need to be presented, as they can be
explained in the same way, and you can easily modify the last example yourself
to see that :math:`O(n^2)` is true. Instead, let us take a broader view and
estimate the time spent on performing a full start of all processes (the notify
case).

.. code:: python

    #!/usr/bin/env python3

    import multiprocessing
    import sys
    import time


    def main():
        n = int(sys.argv[1])  # the number of processes
        started = multiprocessing.Array("b", n, lock=False)

        def work(i):
            started[i] = True

            while not all(started):  # wait for the other processes
                time.sleep(0)  # do some work

        processes = [
            multiprocessing.Process(target=work, args=[i])
            for i in range(n)
        ]
        start_time = time.perf_counter()

        for process in processes:  # start all processes
            process.daemon = True
            process.start()

        for process in processes:  # join all processes
            process.join()
            process.close()

        print(time.perf_counter() - start_time)  # elapsed time in seconds


    if __name__ == "__main__":
        multiprocessing.set_start_method("fork")
        sys.exit(main())

.. tab:: CPython

  .. table::
    :class: widetable

    +---------------+------------------------+--------------------+
    | n (processes) | elapsed time (seconds) |       factor       |
    +===============+========================+====================+
    |       10      |   00.017279455903918   | 01.000000000000000 |
    +---------------+------------------------+--------------------+
    |       20      |   00.046516090165824   | 02.691988128820520 |
    +---------------+------------------------+--------------------+
    |       30      |   00.112311841920018   | 06.499732546240368 |
    +---------------+------------------------+--------------------+
    |       40      |   00.237931306008250   | 13.769606365574647 |
    +---------------+------------------------+--------------------+
    |       50      |   00.410052322316915   | 23.730626970953920 |
    +---------------+------------------------+--------------------+
    |       60      |   00.648528296034783   | 37.531754451119640 |
    +---------------+------------------------+--------------------+
    |       70      |   00.939843381755054   | 54.390797197611720 |
    +---------------+------------------------+--------------------+
    |       80      |   01.276011181063950   | 73.845564823291470 |
    +---------------+------------------------+--------------------+
    |       90      |   01.661460759118199   | 96.152377039922740 |
    +---------------+------------------------+--------------------+

.. tab:: PyPy

  .. table::
    :class: widetable

    +---------------+------------------------+--------------------+
    | n (processes) | elapsed time (seconds) |       factor       |
    +===============+========================+====================+
    |       10      |   00.100632547866553   | 01.000000000000000 |
    +---------------+------------------------+--------------------+
    |       20      |   00.421639931853861   | 04.189896219392054 |
    +---------------+------------------------+--------------------+
    |       30      |   00.950271079782397   | 09.442979432882224 |
    +---------------+------------------------+--------------------+
    |       40      |   01.685608274769038   | 16.750130156739065 |
    +---------------+------------------------+--------------------+
    |       50      |   03.188453416805714   | 31.684116962176716 |
    +---------------+------------------------+--------------------+
    |       60      |   04.502324510365725   | 44.740241659549080 |
    +---------------+------------------------+--------------------+
    |       70      |   05.979793237987906   | 59.422059410814060 |
    +---------------+------------------------+--------------------+
    |       80      |   07.862899474799633   | 78.134755022067780 |
    +---------------+------------------------+--------------------+
    |       90      |   10.051243904046714   | 99.880646144182690 |
    +---------------+------------------------+--------------------+

Even though we use processes instead of threads, thereby bypassing the GIL, we
still have :math:`O(n^2)`. The explanation for this is quite simple.

Let us suppose we have :math:`k` cores and :math:`n` processes. The main
process runs on one of these cores. :math:`min(k-1,n)` processes can be
assigned to the remaining :math:`k-1` cores, and everything will run in
parallel for :math:`O(n)`. But as soon as all cores are loaded, further process
starts will not be parallelized, and the scheduler will create a separate
execution queue for each core. As a result, if we have a uniform distribution
of :math:`n` processes across :math:`k` cores, the main process will multitask
with :math:`n/k` processes, which is :math:`O(n^2/k)`. And since we consider
:math:`k` to be a constant value, this simplifies to just :math:`O(n^2)`.

What if we have a non-uniform distribution? Let us suppose that the main
process runs on the 1st core, and all the others are distributed across
:math:`k-1` cores. Then it depends on how each process is started: if the main
process does not wait for each one to start, then it is :math:`O(n)`, otherwise
:math:`O(n^2)`.

So, what can we say about the notify case? If we start/wake up/notify :math:`n`
execution units, and :math:`n` is greater than :math:`k` cores (while
considering the GIL as a single-core environment), then:

1. If the operation is free (does not require context switching), then we have
   amortized :math:`O(n)`.
2. If the operation requires context switching but does not wait for an
   execution unit, then we have :math:`O(n)` in the non-uniform case and
   :math:`O(n^2)` in the uniform case.
3. If the operation waits for an execution unit, then we have :math:`O(n^2)`.

Well, we have covered one half of the square problem. But what can we say about
the mutex case for processes? Let us take measurements on CPython with
different numbers of allocated cores.

.. code:: python

    #!/usr/bin/env python3

    import multiprocessing
    import sys
    import time


    def main():
        n = int(sys.argv[1])  # the number of processes
        active = multiprocessing.Array("b", n, lock=False)
        start_time = multiprocessing.Value("d", 0, lock=False)
        lock = multiprocessing.Lock()

        def work(i):
            active[i] = True

            with lock:
                if not start_time:
                    while not all(active):  # wait for the other processes
                        time.sleep(0)  # (via polling)

                    start_time.value = time.perf_counter()

            active[i] = False

            while any(active):  # wait for the other processes
                time.sleep(0)  # do some work

        processes = [
            multiprocessing.Process(target=work, args=[i])
            for i in range(n)
        ]

        for process in processes:  # start all processes
            process.daemon = True
            process.start()

        for process in processes:  # join all processes
            process.join()
            process.close()

        start_time = start_time.value
        print(time.perf_counter() - start_time)  # elapsed time in seconds


    if __name__ == "__main__":
        multiprocessing.set_start_method("fork")
        sys.exit(main())

.. tab:: single-core

  .. table::
    :class: widetable

    +---------------+------------------------+--------------------+
    | n (processes) | elapsed time (seconds) |       factor       |
    +===============+========================+====================+
    |       40      |   00.067960618995130   | 01.000000000000000 |
    +---------------+------------------------+--------------------+
    |       80      |   00.139459939673543   | 02.052069885995836 |
    +---------------+------------------------+--------------------+
    |      120      |   00.215381144080311   | 03.169205155352468 |
    +---------------+------------------------+--------------------+
    |      160      |   00.265911656897515   | 03.912731532309466 |
    +---------------+------------------------+--------------------+
    |      200      |   00.294114463962615   | 04.327719027745911 |
    +---------------+------------------------+--------------------+
    |      240      |   00.392454196698964   | 05.774729578715082 |
    +---------------+------------------------+--------------------+
    |      280      |   00.618052370846272   | 09.094272241554481 |
    +---------------+------------------------+--------------------+
    |      320      |   01.023123964201659   | 15.054659291360695 |
    +---------------+------------------------+--------------------+
    |      360      |   01.478573990985751   | 21.756334960570374 |
    +---------------+------------------------+--------------------+

.. tab:: dual-core

  .. table::
    :class: widetable

    +---------------+------------------------+--------------------+
    | n (processes) | elapsed time (seconds) |       factor       |
    +===============+========================+====================+
    |       40      |   00.035231948364526   | 01.000000000000000 |
    +---------------+------------------------+--------------------+
    |       80      |   00.072951771784574   | 02.070614177501086 |
    +---------------+------------------------+--------------------+
    |      120      |   00.116259925998747   | 03.299843789388778 |
    +---------------+------------------------+--------------------+
    |      160      |   00.152027308940887   | 04.315041205440658 |
    +---------------+------------------------+--------------------+
    |      200      |   00.195907999761403   | 05.560521312487400 |
    +---------------+------------------------+--------------------+
    |      240      |   00.239239112008363   | 06.790402549784772 |
    +---------------+------------------------+--------------------+
    |      280      |   00.268752446863800   | 07.628089258168840 |
    +---------------+------------------------+--------------------+
    |      320      |   00.313643676228821   | 08.902251813715175 |
    +---------------+------------------------+--------------------+
    |      360      |   00.402980351820588   | 11.437924115100506 |
    +---------------+------------------------+--------------------+

All this time, we have been using a simplified execution model, which can be
described as round-robin scheduling - :abbr:`FIFO (first-in, first-out)`
execution order, static priorities (remember, we never mentioned them?), fixed
timeslices. This model describes multithreading under the GIL quite well due to
the tendency of modern CPU schedulers to be fair, and we were even able to use
it to interpret the notify case outside the GIL. But real multitasking is more
complicated, and we see that clearly.

In modern CPU schedulers, timeslices can be adjusted in real time. For example,
:abbr:`CFS (Completely Fair Scheduler)` attempts to distribute time fairly
across all processes, and accordingly, timeslices decrease as the number of
processes increases. This can turn :math:`O(n^2)` into :math:`O(n)`, because
the same amount of time will be allocated for each pass of the scheduler - in
an ideal case. In reality, however, timeslices have their own minimum, and with
a sufficiently large number of execution units, we will meet the square again.

Another feature is dynamic priorities, calculated during execution. They can be
specified explicitly, or they can be a consequence of the internal structure of
the scheduler (such as the use of red-black trees). This also helps mitigate
the square problem.

.. note::

    `Free-threading <https://docs.python.org/3/howto/
    free-threading-python.html>`__ execution is similar to process execution in
    terms of scheduling, as it is also not affected by the GIL, and as a
    result, it produces less convenient (and more chaotic) results for
    interpretation. That is why we did not consider free-threading at all.

    Nevertheless, based on the measurement results, you can see that
    free-threading is also subject to the square problem, albeit to a lesser
    extent.

Let us repeat the measurements, but this time with SCHED_RR as the scheduling
policy.

.. tab:: single-core

  .. table::
    :class: widetable

    +---------------+------------------------+--------------------+
    | n (processes) | elapsed time (seconds) |       factor       |
    +===============+========================+====================+
    |       40      |   00.027295151725411   | 01.000000000000000 |
    +---------------+------------------------+--------------------+
    |       80      |   00.079090036917478   | 02.897585538747751 |
    +---------------+------------------------+--------------------+
    |      120      |   00.173605100251734   | 06.360290721158010 |
    +---------------+------------------------+--------------------+
    |      160      |   00.326644965447485   | 11.967142323791643 |
    +---------------+------------------------+--------------------+
    |      200      |   00.553181726951152   | 20.266666128701070 |
    +---------------+------------------------+--------------------+
    |      240      |   00.868360341992229   | 31.813721012724670 |
    +---------------+------------------------+--------------------+
    |      280      |   01.290889627300203   | 47.293733344533930 |
    +---------------+------------------------+--------------------+
    |      320      |   01.827823021914810   | 66.965116746837180 |
    +---------------+------------------------+--------------------+
    |      360      |   02.501605851110071   | 91.650190344284110 |
    +---------------+------------------------+--------------------+

.. tab:: dual-core

  .. table::
    :class: widetable

    +---------------+------------------------+--------------------+
    | n (processes) | elapsed time (seconds) |       factor       |
    +===============+========================+====================+
    |       40      |   00.015457837842405   | 01.000000000000000 |
    +---------------+------------------------+--------------------+
    |       80      |   00.044563175644726   | 02.882885439674963 |
    +---------------+------------------------+--------------------+
    |      120      |   00.094910128973424   | 06.139935606845444 |
    +---------------+------------------------+--------------------+
    |      160      |   00.176434612832963   | 11.413925714045062 |
    +---------------+------------------------+--------------------+
    |      200      |   00.297088406980037   | 19.219273096852360 |
    +---------------+------------------------+--------------------+
    |      240      |   00.461523207835853   | 29.856905767880143 |
    +---------------+------------------------+--------------------+
    |      280      |   00.668943003285676   | 43.275328031362360 |
    +---------------+------------------------+--------------------+
    |      320      |   00.938138597644866   | 60.690156489500040 |
    +---------------+------------------------+--------------------+
    |      360      |   01.287928364239633   | 83.318791241716410 |
    +---------------+------------------------+--------------------+

You may have occasionally encountered claims that multithreading in Python is
somehow "not quite right", that certain cases have strangely low performance
(usually the notify case), but these claims were not backed up by any clear
arguments. Well, now they will be. Let us highlight some of Python's
multithreading performance issues:

1. Low adaptability of the GIL - lack of dynamic switching intervals and
   priorities, which leads to the square problem in its pure form. For
   comparison, many other languages rely on the OS-level scheduler and, as a
   result, inherit its advantages.
2. All primitives from the :mod:`threading` module are implemented via a mutex
   (:class:`threading.Lock`), which creates the square problem even where it
   might not have been there. For comparison, primitives in Java are
   implemented via atomic :abbr:`CAS (compare-and-swap)`.
3. Acquire-release after waiting in :meth:`condition.wait()
   <threading.Condition.wait>` - well, this is a general problem with this
   primitive, and there is nothing we can do.

.. admonition:: Do you need to go deeper?

    We have covered far from all aspects of the GIL that affect performance;
    there are others. If you want to learn more about the GIL and its effect on
    multithreading, there is a good `Python behind the scenes <https://
    tenthousandmeters.com/tag/python-behind-the-scenes/>`__ series by Victor
    Skvortsov, which is a dive into the internals of CPython.

    You may also be interested in `one faster-cpython/ideas discussion
    <https://github.com/faster-cpython/ideas/discussions/328>`__.

It is time to arm ourselves and take control of the square problem into our own
hands.

Kill the square
+++++++++++++++

Check back later!
