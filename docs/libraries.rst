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
---------------------------

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

Why are the release methods not asynchronous?
+++++++++++++++++++++++++++++++++++++++++++++

Once we have dealt with the previous question, we are bound to come to the
next, equally difficult question in software design: should we represent the
entire asynchronous API as coroutine functions? It refers to one of the most
important ideas from software architecture, called "`separation of concerns
<https://en.wikipedia.org/wiki/Separation_of_concerns>`_", and is a strict form
of API separation. It is the curio way, and it directly affects release
methods, such as ``release()``.

Let's assume that we decided to make release methods as coroutine functions.
Then we will be able to use any asynchronous API in such methods to create any
complex logic, which opens the way to implementing primitives like
:class:`eventlet.semaphore.CappedSemaphore`, whose release methods can be
blocking. This is a strong advantage, but let's move on to the disadvantages:

1. More complex cancellation handling. Because release methods are used after
   acquire methods, they must always be fully executed, which would require
   shielding release method calls from cancellation. Otherwise, cancelling a
   release method call (e.g. due to its blocking nature or a checkpoint) will
   result in the primitive no longer being able to be acquired.
2. A cascade effect. Coroutine functions can only be used from coroutines - the
   async/await syntax says so. As a consequence, in addition to splitting
   ``event.set()`` into ``event.green_set()`` and ``event.async_set()``, any
   code that used ``event.set()`` in an asynchronous environment must also
   become asynchronous. This problem has long been `a source of friction in
   anyio <https://github.com/agronholm/anyio/issues/179>`_, resulting in its
   `dropping curio support <https://github.com/agronholm/anyio/pull/182>`_.
3. Just lower performance. With checkpoints enabled, any code that uses several
   primitives in a row will switch context several times in a row even if there
   is no workload between context switches. For example, if ``acquire()`` comes
   right after ``release()``.

Due to these disadvantages, aiologic does not use async/await syntax where it
can be done without it, which is the same approach as asyncio, trio, and other
libraries other than curio. However, while aiologic does not follow the curio
way, it fully supports curio, although not with interfaces native to its
architectural model.

How does aiologic import libraries?
-----------------------------------

aiologic is strong in that it efficiently supports the wide variety of
concurrency libraries without depending on any of them. The techniques it uses
for this purpose resemble `lazy imports <https://peps.python.org/pep-0690/>`_
in action, but differ from them in flexibility and higher efficiency.

The first of them may have different names, but let us call it "global
rebinding". When you call an aiologic function that needs to access a
third-party library's API, on the first call it does all the necessary imports
and replaces itself at the module level with the actual implementation. This
eliminates the need to import optional libraries that are not currently
required.

Here is how, for example, a function to check that there is a running
`twisted`_ reactor in the current thread can be implemented:

.. code:: python

    def _twisted_running() -> bool:
        global _twisted_running

        from twisted.python.threadable import isInIOThread

        _twisted_running = isInIOThread  # global rebinding

        return _twisted_running()

One serious disadvantage of this example is that if you do not use twisted, you
have to install it anyway, because otherwise :exc:`ImportError` will be raised.
Well, there are several ways to solve this problem.

The naive one is to suppress the exception and return a default value instead.
Despite its simplicity, it is very, very slow because each time it is called,
it runs the complex `import system <https://docs.python.org/3/reference/
import.html>`_ that can make a lot of file system calls.

.. code:: python

    def _twisted_running() -> bool:
        global _twisted_running

        try:
            import twisted.internet
        except ImportError:  # reactor is not in use
            return False

        from twisted.python.threadable import isInIOThread

        _twisted_running = isInIOThread  # global rebinding

        return _twisted_running()

The other is to check :data:`sys.modules` for the imported module. It is much
better than the naive way and gives performance almost comparable to a direct
return of a default value, but only almost, which may matter when calling
several functions at a time.

.. code:: python

    def _twisted_running() -> bool:
        global _twisted_running

        if "twisted.internet" not in sys.modules:  # reactor is not in use
            return False

        from twisted.python.threadable import isInIOThread

        _twisted_running = isInIOThread  # global rebinding

        return _twisted_running()

Thus, we come to the second technique. That is post import hooks (:pep:`369`)
by `wrapt`_. These allow to use a very fast dummy function before importing a
third-party library on the side, and then replace it with a function that does
the imports on the first call according to the first technique. This
combination of techniques bypasses the need to import when it is known that the
library has not yet started to be used, and also preserves proper exception
propagation.

With the second technique, the example can be improved as follows:

.. code:: python

    from wrapt import when_imported

    def _twisted_running() -> bool:
        return False

    @when_imported("twisted.internet")
    def _(_):  # post import hook
        global _twisted_running

        def _twisted_running():  # global rebinding
            global _twisted_running

            from twisted.python.threadable import isInIOThread

            _twisted_running = isInIOThread  # global rebinding

            return _twisted_running()

The result is the following semantics: libraries are imported when functions
are called, and only when the libraries are actually required. Combined with
aiologic's architecture, this gives us one interesting effect: primitives can
work without needing to import any optional libraries at all. For example, if a
lock is only used in one task at a time, that is, non-blocking.

In addition to these techniques, aiologic also uses
:func:`functools.update_wrapper` to copy original function information, such as
annotations and docstrings, into replacement functions, but removes the
``__wrapped__`` attribute to eliminate memory leaks when a function is called
by many threads at a time.

.. note::

    As a careful reader may notice, functions built on any of the techniques
    cannot be imported directly, since they are only replaced at the level of
    their module. In fact, aiologic uses such functions indirectly, to build
    more general abstractions based on them.

.. hint::

    One consequence is that the fewer libraries you import, the faster aiologic
    runs.

.. _twisted: https://twisted.org/
.. _wrapt: https://wrapt.readthedocs.io/en/master/

How does aiologic detect libraries?
-----------------------------------

The example given during the previous question showed one of the cases of
checking that a library is "running", and it is for a reason. Using similar
functions, aiologic implements detection of the currently running library - the
one whose API should be used to create a waiter or get the current task.

.. autofunction:: aiologic.lowlevel.current_green_library
.. autofunction:: aiologic.lowlevel.current_async_library

.. py:exception:: aiologic.lowlevel.GreenLibraryNotFoundError

  Bases: :exc:`RuntimeError`

  Exception raised by the :func:`aiologic.lowlevel.current_green_library`
  function if the current green library was not recognized.
.. py:exception:: aiologic.lowlevel.AsyncLibraryNotFoundError

  Bases: :exc:`RuntimeError`

  Exception raised by the :func:`aiologic.lowlevel.current_async_library`
  function if the current async library was not recognized.

When are libraries counted as running?
++++++++++++++++++++++++++++++++++++++

Libraries are counted as "currently running" in the current thread by the
following semantics:

* threading: always running
* eventlet: running if there is a hub
* gevent: running if there is a hub
* asyncio: running if :func:`asyncio.get_running_loop` returns a
  non-:data:`None` object
* curio: running if :func:`curio.meta.curio_running` returns :data:`True`
* trio: running if :func:`trio.lowlevel.in_trio_run` returns :data:`True`

It is much clearer in action. The green libraries except threading are counted
as currently running if at least one of their functions that touches the
current hub has been called, such as :func:`eventlet.sleep` or
:func:`gevent.spawn`.

.. code:: python

    >>> aiologic.lowlevel.current_green_library()
    'threading'
    >>> eventlet.spawn(eventlet.sleep)
    <GreenThread object at 0x7ff1db690200 (otid=0x(nil)) pending>
    >>> aiologic.lowlevel.current_green_library()
    'eventlet'
    >>> gevent.spawn(gevent.sleep)
    <Greenlet at 0x7ff1db5191c0: sleep>
    >>> aiologic.lowlevel.current_green_library()
    'gevent'

The async libraries are counted as currently running if the function was called
in an active library run (:func:`asyncio.run` / :func:`curio.run` /
:func:`trio.run` / :func:`anyio.run`).

.. code:: python

    >>> async def test() -> str:
    ...     return aiologic.lowlevel.current_async_library()
    ...
    >>> asyncio.run(test())
    'asyncio'
    >>> curio.run(test)
    'curio'
    >>> trio.run(test)
    'trio'
    >>> anyio.run(test, backend="asyncio")
    'asyncio'
    >>> anyio.run(test, backend="trio")
    'trio'

In case there are several running libraries, priority is given to the one that
is lower in the list (newer). This was already shown in the green libraries
example, where both eventlet and gevent hubs coexisted at the same time. A
similar situation for async libraries is nested ``run()`` calls.

.. note::

    Due to the fact that threading is always counted as running,
    :func:`~aiologic.lowlevel.current_green_library` will always be able to
    recognize the current green library. As a consequence, the ``failsafe``
    parameter has no effect, and
    :exc:`~aiologic.lowlevel.GreenLibraryNotFoundError` is actually useless.
    Nevertheless, they are still present for consistency.

How to manually specify a library as running?
+++++++++++++++++++++++++++++++++++++++++++++

There are situations where you need to explicitly specify the currently running
library. For example, if you are migrating from eventlet to gevent, so you have
eventlet and gevent hubs coexisting in the same thread, and you want to switch
between them. For these situations, aiologic provides thread-local objects with
which you can explicitly set the name of any supported library for the current
thread.

.. py:data:: aiologic.lowlevel.current_green_library_tlocal
  :type: threading.local

  Thread-local data to control the return value of
  :func:`aiologic.lowlevel.current_green_library`.

  .. py:attribute:: aiologic.lowlevel.current_green_library_tlocal.name
    :type: str | None
    :value: None

    Unless set to a non-:data:`None` object, the function detects the current
    green library with its own algorithms. Otherwise the function returns
    exactly the set object.

  .. rubric:: Example

  .. code:: python

    library = aiologic.lowlevel.current_green_library_tlocal.name

    aiologic.lowlevel.current_green_library_tlocal.name = "somelet"

    try:
        ...  # aiologic.lowlevel.current_green_library() == "somelet"
    finally:
        aiologic.lowlevel.current_green_library_tlocal.name = library

.. py:data:: aiologic.lowlevel.current_async_library_tlocal
  :type: threading.local

  Thread-local data to control the return value of
  :func:`aiologic.lowlevel.current_async_library`.

  .. py:attribute:: aiologic.lowlevel.current_async_library_tlocal.name
    :type: str | None
    :value: None

    Unless set to a non-:data:`None` object, the function detects the current
    async library with its own algorithms. Otherwise the function returns
    exactly the set object.

  .. rubric:: Example

  .. code:: python

    library = aiologic.lowlevel.current_async_library_tlocal.name

    aiologic.lowlevel.current_async_library_tlocal.name = "someio"

    try:
        ...  # aiologic.lowlevel.current_async_library() == "someio"
    finally:
        aiologic.lowlevel.current_async_library_tlocal.name = library

It is worth noting that
:data:`aiologic.lowlevel.current_async_library_tlocal.name` is the same as
:data:`sniffio.thread_local.name`. So you can specify the current async library
via either aiologic or sniffio. This is how trio and `trio-asyncio`_ detection
is implemented.

.. tip::

    If the performance of library detection is critical for you, you could
    manually specify a library even when it can be recognized automatically.
    This way the function will not use its own, slower, detection algorithms.

.. _trio-asyncio: https://trio-asyncio.readthedocs.io/en/stable/

Is runtime installation supported?
----------------------------------

When it comes to user scripts, there are different approaches to dependency
management. One of them is to install missing dependencies `straight within a
script <https://stackoverflow.com/q/12332975>`_. But its ambiguous weakness is
that it requires a special approach to optional dependency management on the
side of the packages being installed, depending on where it is applied.

A good example would be the `httpx`_ package. It optionally supports decoding
for "zstd" compressed responses via the `zstandard`_ package, `using the
following module-level code <https://github.com/encode/httpx/blob/
47f4a96ffaaaa07dca1614409549b5d7a6e7af49/httpx/_decoders.py#L29-L33>`_:

.. code:: python

    # Zstandard support is optional
    try:
        import zstandard
    except ImportError:  # pragma: no cover
        zstandard = None  # type: ignore

If a user script installs zstandard after importing httpx, the support will not
be enabled.

The problem is taken into account in the aiologic design. You can install it
and its optional dependencies both before and after importing, and even in
parallel during use, which is achieved by using `the techniques described above
<#how-does-aiologic-import-libraries>`_.

.. note::

    Of course, this is not the main reason why aiologic does not use the
    module-level approach. If it tried to import all supported optional
    dependencies at initialization time, this could lead to either conflicts
    (such as `between eventlet and trio <https://github.com/python-trio/trio/
    issues/3015>`_) or incompatibility with their unsupported versions, even if
    they are not needed by the user.

.. _httpx: https://www.python-httpx.org/
.. _zstandard: https://python-zstandard.readthedocs.io/en/stable/
