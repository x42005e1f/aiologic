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

Currently, aiologic supports the following concurrency libraries:

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

While `anyio`_ runs on top of either `asyncio`_ or `trio`_, it implements
trio-like `structured concurrency <https://en.wikipedia.org/wiki/
Structured_concurrency>`_ with `a different cancellation semantics <https://
anyio.readthedocs.io/en/stable/cancellation.html
#differences-between-asyncio-and-anyio-cancellation-semantics>`_ than
asyncio. Therefore, aiologic has to support both semantics for asyncio at the
same time by using anyio features when they are available.

.. _anyio: https://anyio.readthedocs.io
.. _asyncio: https://docs.python.org/3/library/asyncio.html
.. _trio: https://trio.readthedocs.io

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
operate. In order to support `multiprocessing`_, new approaches are needed.

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

.. _multiprocessing: https://docs.python.org/3/library/multiprocessing.html

Why are the APIs separated?
+++++++++++++++++++++++++++

Different approaches to providing both synchronous and asynchronous APIs
coexist in the wild. In contrast to API separation, which implies using
different functions for different types of libraries, there is an approach of
providing functionality for different worlds via the same functions behaving
differently in different contexts (returning awaitable objects in an
asynchronous context and plain values in others). This improves both
compatibility and usability, but has some non-trivial drawbacks:

1. Such dual nature is bad for static type checking. Let's imagine a function,
   such as ``acquire()``, that returns :class:`bool` in a synchronous context.
   If it were to return :class:`Awaitable[bool] <collections.abc.Awaitable>` in
   an asynchronous context, its actual return type would be a union of both
   types. This raises a question about whether to allow the :keyword:`await`
   expression for objects of that type. If allowed, a type checker might miss a
   situation where an object is not actually an awaitable object, resulting in
   a type error. If disallowed, the :keyword:`await` expression can be used
   only after runtime type checking (or after type casting), which is
   inconvenient for the user.
2. One of the simplest ways to implement such behavior is to check that there
   is a running event loop of an asynchronous library in the current thread.
   This makes the behavior runtime dependent, which in turn can lead to
   undefined behavior. Suppose it is implemented by some library that is used
   by some other, non-asynchronous library that does not inherit this behavior.
   Then accidental use of the second library in an asynchronous context will
   activate the asynchronous API that is not expected by the library, and this
   in turn will lead to errors, perhaps even hard-to-detect ones (e.g. in case
   of ``wait()``-like methods).
3. A more correct way is to check that functions are used from a coroutine,
   which is particularly `implemented by curio <https://curio.readthedocs.io/
   en/stable/reference.html#asynchronous-metaprogramming>`_. This makes the
   behavior less runtime dependent, but still has some nuances. First, it
   prevents calling the asynchronous version of a function from synchronous
   functions, making it incompatible with wrappers (such as
   :func:`functools.partial`, but in pure Python for curio implementation due
   to `special handling of list comprehensions and generator expressions
   <https://github.com/dabeaz/curio/blob/
   98550b94055ccd98406105dd999973a2f2462ea4/curio/meta.py#L65-L75>`_). Second,
   this check negatively affects performance, especially on PyPy, where the
   difference can be a hundredfold or more.

The API separation has drawbacks too, but they are `related to the development
process <https://discuss.python.org/t/15014>`_ rather than runtime specifics.
