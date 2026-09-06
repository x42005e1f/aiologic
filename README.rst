..
  SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
  SPDX-License-Identifier: CC-BY-4.0

.. role:: class(literal)
.. role:: exc(literal)
.. role:: mod(literal)

========
aiologic
========

|pypi-dw| |pypi-impl| |pypi-pyv| |pypi-types|

.. |pypi-dw| image:: https://img.shields.io/pypi/dw/aiologic
  :target: https://pypistats.org/packages/aiologic
  :alt:
.. |pypi-impl| image:: https://img.shields.io/pypi/implementation/aiologic
  :target: #features
  :alt:
.. |pypi-pyv| image:: https://img.shields.io/pypi/pyversions/aiologic
  :target: #features
  :alt:
.. |pypi-types| image:: https://img.shields.io/pypi/types/aiologic
  :target: #features
  :alt:

.. description-start-marker

**aiologic** is a locking library for tasks synchronization and their
communication. It provides primitives that are both *async-aware* and
*thread-aware*, and can be used for interaction between:

- async codes (async <-> async) in one thread as regular async primitives
- async codes (async <-> async) in multiple threads (!)
- async code and sync one (async <-> sync) in one thread (!)
- async code and sync one (async <-> sync) in multiple threads (!)
- sync codes (sync <-> sync) in one thread as regular sync primitives
- sync codes (sync <-> sync) in multiple threads as regular sync primitives

Let's take a look at the example:

.. code:: python

    import asyncio

    from threading import Thread

    import aiologic

    lock = aiologic.Lock()


    async def func(i: int, j: int) -> None:
        print(f"thread={i} task={j} start")

        async with lock:
            await asyncio.sleep(1)

        print(f"thread={i} task={j} end")


    async def main(i: int) -> None:
        await asyncio.gather(func(i, 0), func(i, 1))


    Thread(target=asyncio.run, args=[main(0)]).start()
    Thread(target=asyncio.run, args=[main(1)]).start()

It prints something like this:

.. code-block::

    thread=0 task=0 start
    thread=1 task=0 start
    thread=0 task=1 start
    thread=1 task=1 start
    thread=0 task=0 end
    thread=1 task=0 end
    thread=0 task=1 end
    thread=1 task=1 end

As you can see, tasks from different event loops are all able to acquire
:class:`aiologic.Lock`. In the same case if you use :class:`asyncio.Lock`, it
will raise a :exc:`RuntimeError`. And :class:`threading.Lock` will cause a
deadlock.

.. description-end-marker

Features
========

.. features-start-marker

* Python 3.8+ support
* `CPython <https://www.python.org/>`__ and `PyPy <https://pypy.org/>`__
  support
* Experimental `Nuitka <https://nuitka.net/>`__ support
* `Pickling <https://docs.python.org/3/library/pickle.html>`__ and `weakrefing
  <https://docs.python.org/3/library/weakref.html>`__ support
* Cancellation and timeouts support
* Optional `Trio-style checkpoints <https://trio.readthedocs.io/en/stable/
  reference-core.html#checkpoints>`__:

  * enabled by default for Trio itself
  * disabled by default for all others

* Only one checkpoint per asynchronous call:

  * exactly one context switch if checkpoints are enabled
  * zero or one context switch if checkpoints are disabled

* Fairness wherever possible (with some caveats)
* Thread-safety wherever possible
* Lock-free implementation (with some exceptions)
* Bundled stub files

Synchronization primitives:

* Events: one-time, reusable, and countdown
* Barriers: single-use, cyclic, and reusable
* Semaphores: counting, bounded, and binary
* Capacity limiters: borrowable, and reentrant
* Locks: ownable, and reentrant
* `Readers-writer locks (external) <https://gist.github.com/x42005e1f/
  a50d0744013b7bbbd7ded608d6a3845b>`__
* Condition variables

Communication primitives:

* Queues: FIFO, LIFO, and priority

Non-blocking primitives:

* Flags
* Resource guards
* `Futures (external) <https://gist.github.com/x42005e1f/
  4f18c3c62da9135020bdea8c44c248a2>`__

Supported concurrency libraries:

.. libraries-start-marker

* `asyncio`_, `curio`_, `trio`_, and `anyio`_ (coroutine-based)
* `eventlet`_, and `gevent`_ (greenlet-based)
* `threading`_ (thread-based)

.. _asyncio: https://docs.python.org/3/library/asyncio.html
.. _curio: https://curio.readthedocs.io
.. _trio: https://trio.readthedocs.io
.. _anyio: https://anyio.readthedocs.io
.. _eventlet: https://eventlet.readthedocs.io
.. _gevent: https://www.gevent.org/
.. _threading: https://docs.python.org/3/library/threading.html

.. libraries-end-marker

Free threading
--------------

The GIL ensures `sequential consistency <https://en.wikipedia.org/wiki/
Sequential_consistency>`__ of all operations due to `the synchronizes-with
relation <https://preshing.com/20130823/the-synchronizes-with-relation/>`__,
and this allows the execution of Python code to be interpreted as one of the
possible serialized sequences of all threads' operations. In addition, there
are also effectively atomic operations (those at the C level that do not
release the GIL), and the pure-Python implementation of this library takes
advantage of this.

In `free-threaded Python <https://docs.python.org/3/howto/
free-threading-python.html>`__, the same subset of effectively atomic
operations we use `remains thread-safe <https://docs.python.org/3/library/
threadsafety.html>`__; however, one nuance is that sequential consistency is no
longer guaranteed, and we may observe weaker ordering on relaxed operations.

The pure-Python implementation is primarily designed for the GIL (sequential
consistency) and targets `x86-TSO <https://www.cl.cam.ac.uk/~pes20/weakmemory/
index3.html>`__ or stronger (x86, x86-64, s390x, etc.) where ordering may be in
question in the current free-threading implementation. If you need stricter
guarantees, please prefer the build with extension modules when it is
available.

.. features-end-marker

Installation
============

.. installation-start-marker

Install from `PyPI <https://pypi.org/project/aiologic/>`__ (stable):

.. code:: console

    pip install aiologic

Or from `GitHub <https://github.com/x42005e1f/aiologic>`__ (latest):

.. code:: console

    pip install git+https://github.com/x42005e1f/aiologic.git

You can also use other package managers, such as `uv <https://github.com/
astral-sh/uv>`__.

.. installation-end-marker

Documentation
=============

Read the Docs: https://aiologic.readthedocs.io (official)

There are also related posts:

* https://news.ycombinator.com/item?id=46308839 — how it all began
* https://redd.it/1psjsnu — a brief introduction

Communication channels
======================

GitHub Discussions: https://github.com/x42005e1f/aiologic/discussions (ideas,
questions)

GitHub Issues: https://github.com/x42005e1f/aiologic/issues (bug tracker)

You can also send an email to 0x42005e1f@gmail.com with any feedback.

Project status
==============

The project is developed and maintained by one person in his spare time and is
not a commercial product. The author is not a professional programmer, so you
may encounter some misunderstandings. However, he has been programming as a
hobby for over a decade, delving into specific topics (often esoteric ones),
and until 2024, he made almost no public contributions (you can find some if
you try hard; for example, one very ugly one in Java from 2019), as he set high
standards for himself. The author often makes mistakes, so he constantly
double-checks and improves himself (which is well reflected in how often he
edits his own comments) — as a result, he relies heavily on careful theoretical
analysis and proactive bug fixing.

No AI tools are used in the development (nor are IDE tools, for that matter).
The only exception is text translation, since the author is not a native
English speaker, but the texts themselves are not generated (they are written
and edited manually by a human). Unicode characters are also actively used (via
a compose key), as the author likes beautiful texts, such as they were before
the avoidance of signs of AI writing. *— It may not be too obvious, but this
paragraph addresses the sore subject of "you are an AI", expressed in... not
the best ways.*

It is published for the simple reason that the author considered it noteworthy
and not too ugly. The topic is quite non-trivial, so although contributions are
not prohibited, they will be very, very difficult if you decide to make them
(except for some very simple ones). The functionality provided is still being
perfected, so the development status is alpha.

What is the goal of the project? To realize the author's vision. Is it worth
trusting what is available now? Well, the choice is yours. But the project `is
already being used <https://github.com/x42005e1f/aiologic/discussions/11>`__,
so why not give it a try?

License
=======

.. license-start-marker

The aiologic library is `REUSE-compliant <https://api.reuse.software/info/
github.com/x42005e1f/aiologic>`__ and is offered under multiple licenses:

* All original source code is licensed under `ISC`_.
* All original test code is licensed under `0BSD`_.
* All documentation is licensed under `CC-BY-4.0`_.
* All configuration is licensed under `CC0-1.0`_.

For more accurate information, check the individual files.

.. _ISC: https://choosealicense.com/licenses/isc/
.. _0BSD: https://choosealicense.com/licenses/0bsd/
.. _CC-BY-4.0: https://choosealicense.com/licenses/cc-by-4.0/
.. _CC0-1.0: https://choosealicense.com/licenses/cc0-1.0/

.. license-end-marker
