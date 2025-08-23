..
  SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
  SPDX-License-Identifier: CC-BY-4.0

Performance
===========

You probably came here to see how fast aiologic is. To see detailed
measurements, beautifully drawn with `Matplotlib <https://matplotlib.org/>`_,
such as in `the reply to one issue <https://github.com/x42005e1f/aiologic/
issues/7#issuecomment-3067270072>`_. Well, try to come back another time!

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
it is for parallel computing with NumPy arrays, for network operations, or for
simulating some game processes - it does not matter. Here is an example that
allows us to estimate the time spent on performing a full start of all threads:

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

* ``thread #0 → thread #1`` (starting the first thread)
* ``thread #0 → thread #1 → thread #2`` (starting the second thread)
* ...
* ``thread #0 → thread #1 → ... → thread #(N-1) → thread #(N)`` (starting and
  stopping the last thread)
* ``thread #0 → thread #1 → ... → thread #(N-1)`` (stopping the other threads)
* ``thread #0`` (the end)

In particular, for :math:`n=1`:

* ``thread #0 → thread #1`` (starting and stopping the first/last thread)
* ``thread #0`` (the end)

For :math:`n=3`:

* ``thread #0 → thread #1`` (starting the first thread)
* ``thread #0 → thread #1 → thread #2`` (starting the second thread)
* ``thread #0 → thread #1 → thread #2 → thread #3``  (starting and stopping the
  last thread)
* ``thread #0 → thread #1 → thread #2`` (stopping the other threads)
* ``thread #0`` (the end)

With each new thread, the required number of context switches to start the next
one increases. We see a triangle (:math:`1+2+3+…+n` context switches of the
threads until stopping), which becomes a *square* when the constant is
discarded (:math:`1+2+3+…+n=\frac{n(1+n)}{2}⇒n^2`) - that is where the
quadratic `time complexity <https://en.wikipedia.org/wiki/Time_complexity>`_
comes from!

Our example is not the only one with the square. There are others, also scarily
simple and reproducible. But let us now express the time complexity using `big
O notation <https://en.wikipedia.org/wiki/Big_O_notation>`_ for simplicity.
From this point on, "square" and :math:`O(n^2)` are synonymous.

Squares, squares everywhere
+++++++++++++++++++++++++++

Check back later!
