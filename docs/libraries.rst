..
  SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
  SPDX-License-Identifier: CC-BY-4.0

Libraries
=========

.. note::

    This is the first section on advanced topics that cover the inner workings
    of aiologic as well as some complex scenarios. For the reader's
    convenience, they are in a frequently asked questions (FAQ) format, making
    it easier to find information.

There are several goals that aiologic aims to achieve. One of them is to
provide a convenient "glue" for different multitasking worlds, and thus
different concurrency libraries. When you work with
:class:`concurrent.futures.ThreadPoolExecutor`, you are actually working with
`threading`_. When you work with :class:`aiohttp.ClientSession`, you are
actually working with `asyncio`_. The huge number of asynchronous libraries
available for your use rely on a very small set of "root" concurrency
libraries.

However, the concurrency libraries are usually unaware of each other, making
different asynchronous libraries incompatible with each other. Acting as a
bridge between different worlds, aiologic should be aware of the largest number
of concurrency libraries to cover the maximum number of possible combinations.

.. _asyncio: https://docs.python.org/3/library/asyncio.html
.. _threading: https://docs.python.org/3/library/threading.html

Which libraries does aiologic support?
--------------------------------------

Currently aiologic supports the following libraries:

.. include:: ../README.rst
  :start-after: .. libraries-start-marker
  :end-before: .. libraries-end-marker

But uses a slightly different division in its work:

* coroutine-based libraries are "async" libraries
* greenlet-based and thread-based libraries are "green" libraries

This division is based on the fact that only coroutine-based libraries use
asynchronous functions (:pep:`492`), while the code for thread-based libraries
cannot be distinguished from the code for greenlet-based libraries by function
signatures.

Why is AnyIO mentioned?
+++++++++++++++++++++++

While anyio runs on top of either asyncio or trio, it implements trio-like
`structured concurrency <https://en.wikipedia.org/wiki/
Structured_concurrency>`_ with `a different cancellation semantics <https://
anyio.readthedocs.io/en/stable/cancellation.html
#differences-between-asyncio-and-anyio-cancellation-semantics>`_ than
asyncio. Therefore, aiologic has to support both semantics for asyncio at the
same time by using anyio features when they are available.

Why is Twisted not supported?
+++++++++++++++++++++++++++++

While `twisted`_ has some features of newer concurrency libraries and even
`supports asyncio via a separate reactor <https://meejah.ca/blog/
python3-twisted-and-asyncio>`_, it lacks the concept of a current execution
unit, commonly called a *current task*.

The problem can be illustrated most clearly with the example of
:class:`aiologic.RLock`: how to handle lock acquisitions in different
callbacks? Acquire reentrantly, assuming the entire reactor is one execution
unit? Or acquire non-reentrantly, like
:class:`~twisted.internet.defer.DeferredLock`, assuming that the different
callbacks are different execution units? But then how to distinguish them from
each other?

Since there is no clear way to implement support for twisted that would allow
aiologic primitives to work as native twisted primitives, it is currently not
supported at all. Instead, you can use aiologic with twisted via its asyncio
support.

.. _twisted: https://twisted.org/

Why is multiprocessing not supported?
+++++++++++++++++++++++++++++++++++++

Unlike threads, which share common memory, each process manages its own memory.
This is a different situation than the one in which aiologic primitives
operate. In order to support multiprocessing, new approaches are needed.

There are several ways to enable interactions between processes, such as:

1. Allocate shared memory and rely on operations on it.
2. Use standard communication mechanisms such as pipes or sockets.

The first way is closest to the spirit of aiologic, but has limited scalability
and cannot be implemented via effectively atomic operations in pure Python. The
second way would require implementing an architecture without a server process
to preserve the spirit of aiologic, which is a challenge that requires a
separate research.

Thus, there is no way to easily implement multiprocessing support that would
not conflict with aiologic's ideas. Nevertheless, it is still an open question,
and the situation may change in the future.
