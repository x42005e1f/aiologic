..
  SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
  SPDX-License-Identifier: CC-BY-4.0

.. role:: mod(literal)
.. role:: func(literal)
.. role:: data(literal)
.. role:: const(literal)
.. role:: class(literal)
.. role:: meth(literal)
.. role:: attr(literal)
.. role:: type(literal)
.. role:: exc(literal)
.. role:: obj(literal)

========
aiologic
========

.. badges-start-marker

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

.. badges-end-marker

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
* `CPython <https://www.python.org/>`_ and `PyPy <https://pypy.org/>`_ support
* `Pickling <https://docs.python.org/3/library/pickle.html>`_ and `weakrefing
  <https://docs.python.org/3/library/weakref.html>`_ support
* Cancellation and timeouts support
* Optional `Trio-style checkpoints <https://trio.readthedocs.io/en/stable/
  reference-core.html#checkpoints>`_:

  * enabled by default for Trio itself
  * disabled by default for all others

* Only one checkpoint per asynchronous call:

  * exactly one context switch if checkpoints are enabled
  * zero or one context switch if checkpoints are disabled

* Fairness wherever possible (with some caveats)
* Thread-safety wherever possible
* Lock-free implementation
* Bundled stub files

Synchronization primitives:

* Flags
* Events: low-level, one-time, reusable, and countdown
* Barriers: single-use, and cyclic
* Semaphores: counting, and bounded
* Capacity limiters: borrowable, and reentrant
* Locks: primitive, bounded, ownable, and reentrant
* `Readers-writer locks (external) <https://gist.github.com/x42005e1f/
  a50d0744013b7bbbd7ded608d6a3845b>`_
* Condition variables
* Resource guards

Communication primitives:

* Queues: FIFO, LIFO, and priority

Supported concurrency libraries:

* `asyncio <https://docs.python.org/3/library/asyncio.html>`_, `curio <https://
  curio.readthedocs.io>`_, `trio <https://trio.readthedocs.io>`_, and `anyio
  <https://anyio.readthedocs.io>`_ (coroutine-based)
* `eventlet <https://eventlet.readthedocs.io>`_, and `gevent <https://
  www.gevent.org/>`_ (greenlet-based)
* `threading <https://docs.python.org/3/library/threading.html>`_
  (thread-based)

All synchronization and communication primitives are implemented entirely on
effectively atomic operations, which gives `an incredible speedup on PyPy
<https://gist.github.com/x42005e1f/149d3994d5f7bd878def71d5404e6ea4>`_ compared
to alternatives from the :mod:`threading` module. All this works because of
GIL, but per-object locks also ensure that `the same operations are still
atomic <https://peps.python.org/pep-0703/#container-thread-safety>`_, so
aiologic also works when running in a `free-threaded mode <https://
docs.python.org/3.13/whatsnew/3.13.html#free-threaded-cpython>`_.

.. features-end-marker

Installation
============

.. installation-start-marker

Install from `PyPI <https://pypi.org/project/aiologic/>`_ (recommended):

.. code:: console

    pip install aiologic

Or from `GitHub <https://github.com/x42005e1f/aiologic>`_:

.. code:: console

    pip install git+https://github.com/x42005e1f/aiologic.git

You can also use other package managers, such as `uv <https://github.com/
astral-sh/uv>`_.

.. installation-end-marker

Documentation
=============

Read the Docs: https://aiologic.readthedocs.io (official)

DeepWiki: https://deepwiki.com/x42005e1f/aiologic (AI generated)

Communication channels
======================

GitHub Discussions: https://github.com/x42005e1f/aiologic/discussions

Feel free to post your questions and ideas here.

Support
=======

If you like aiologic and want to support its development, star `its repository
on GitHub <https://github.com/x42005e1f/aiologic>`_.

.. image:: https://starchart.cc/x42005e1f/aiologic.svg?variant=adaptive
  :target: https://starchart.cc/x42005e1f/aiologic

License
=======

.. license-start-marker

The aiologic library is `REUSE-compliant <https://api.reuse.software/info/
github.com/x42005e1f/aiologic>`_ and is offered under multiple licenses:

* All original source code is licensed under `ISC <https://choosealicense.com/
  licenses/isc/>`_.
* All original test code is licensed under `0BSD <https://choosealicense.com/
  licenses/0bsd/>`_.
* All documentation is licensed under `CC-BY-4.0 <https://choosealicense.com/
  licenses/cc-by-4.0/>`_.
* All configuration is licensed under `CC0-1.0 <https://choosealicense.com/
  licenses/cc0-1.0/>`_.

For more accurate information, check the individual files.

.. license-end-marker
