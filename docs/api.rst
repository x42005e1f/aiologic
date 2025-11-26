..
  SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
  SPDX-License-Identifier: CC-BY-4.0

API reference
=============

Synchronization primitives
--------------------------

Events
++++++

.. autoclass:: aiologic.Event
.. autoclass:: aiologic.REvent
.. autoclass:: aiologic.CountdownEvent

Barriers
++++++++

.. autoclass:: aiologic.Latch
.. autoclass:: aiologic.Barrier
.. autoclass:: aiologic.RBarrier
.. autoexception:: aiologic.BrokenBarrierError
  :no-inherited-members:

Semaphores
++++++++++

.. autoclass:: aiologic.Semaphore
.. autoclass:: aiologic.BoundedSemaphore
.. autoclass:: aiologic.BinarySemaphore
.. autoclass:: aiologic.BoundedBinarySemaphore

Capacity limiters
+++++++++++++++++

.. autoclass:: aiologic.CapacityLimiter
.. autoclass:: aiologic.RCapacityLimiter

Locks
+++++

.. autoclass:: aiologic.Lock
.. autoclass:: aiologic.RLock
.. autofunction:: aiologic.synchronized

Condition variables
+++++++++++++++++++

.. autoclass:: aiologic.Condition

Communication primitives
------------------------

Queues
++++++

.. autoclass:: aiologic.SimpleQueue
.. autoclass:: aiologic.SimpleLifoQueue
.. autoclass:: aiologic.Queue
.. autoclass:: aiologic.LifoQueue
.. autoclass:: aiologic.PriorityQueue
.. autoexception:: aiologic.QueueEmpty
  :no-inherited-members:
.. autoexception:: aiologic.QueueFull
  :no-inherited-members:

Non-blocking primitives
-----------------------

Flags
+++++

.. autoclass:: aiologic.Flag

Resource guards
+++++++++++++++

.. autoclass:: aiologic.ResourceGuard
.. autoexception:: aiologic.BusyResourceError
  :no-inherited-members:

Low-level primitives
--------------------

Waiters (low-level)
+++++++++++++++++++

.. autoclass:: aiologic.lowlevel.Waiter
.. autoclass:: aiologic.lowlevel.AsyncWaiter
.. autoclass:: aiologic.lowlevel.GreenWaiter
.. autofunction:: aiologic.lowlevel.create_async_waiter
.. autofunction:: aiologic.lowlevel.create_green_waiter

Events (low-level)
++++++++++++++++++

.. autoclass:: aiologic.lowlevel.Event
.. autoclass:: aiologic.lowlevel.AsyncEvent
.. autoclass:: aiologic.lowlevel.GreenEvent
.. autoclass:: aiologic.lowlevel.SetEvent
  :no-inherited-members:
.. autoclass:: aiologic.lowlevel.DummyEvent
  :no-inherited-members:
.. autoclass:: aiologic.lowlevel.CancelledEvent
  :no-inherited-members:

.. aiologic.lowlevel.SET_EVENT-start-marker
.. data:: aiologic.lowlevel.SET_EVENT
  :type: SetEvent
  :no-index:

  ...
.. aiologic.lowlevel.SET_EVENT-end-marker

.. aiologic.lowlevel.DUMMY_EVENT-start-marker
.. data:: aiologic.lowlevel.DUMMY_EVENT
  :type: DummyEvent
  :no-index:

  ...
.. aiologic.lowlevel.DUMMY_EVENT-end-marker

.. aiologic.lowlevel.CANCELLED_EVENT-start-marker
.. data:: aiologic.lowlevel.CANCELLED_EVENT
  :type: CancelledEvent
  :no-index:

  ...
.. aiologic.lowlevel.CANCELLED_EVENT-end-marker

.. autofunction:: aiologic.lowlevel.create_async_event
.. autofunction:: aiologic.lowlevel.create_green_event

Locks (low-level)
+++++++++++++++++

.. aiologic.lowlevel.ThreadLock-start-marker
.. class:: aiologic.lowlevel.ThreadLock
  :final:
  :no-index:

  Bases: :class:`object`

  The return type of :func:`~aiologic.lowlevel.create_thread_lock`.
.. aiologic.lowlevel.ThreadLock-end-marker

.. aiologic.lowlevel.ThreadRLock-start-marker
.. class:: aiologic.lowlevel.ThreadRLock
  :final:
  :no-index:

  Bases: :class:`object`

  The return type of :func:`~aiologic.lowlevel.create_thread_rlock`.
.. aiologic.lowlevel.ThreadRLock-end-marker

.. aiologic.lowlevel.ThreadOnceLock-start-marker
.. class:: aiologic.lowlevel.ThreadOnceLock
  :final:
  :no-index:

  Bases: :class:`object`

  The return type of :func:`~aiologic.lowlevel.create_thread_oncelock`.
.. aiologic.lowlevel.ThreadOnceLock-end-marker

.. aiologic.lowlevel.ThreadDummyLock-start-marker
.. class:: aiologic.lowlevel.ThreadDummyLock
  :final:
  :no-index:

  Bases: :class:`object`

  A singleton class for :data:`~aiologic.lowlevel.THREAD_DUMMY_LOCK`.
.. aiologic.lowlevel.ThreadDummyLock-end-marker

.. aiologic.lowlevel.THREAD_DUMMY_LOCK-start-marker
.. data:: aiologic.lowlevel.THREAD_DUMMY_LOCK
  :type: ThreadDummyLock
  :no-index:

  A singleton object that mimics a reentrant lock but does nothing.

  Can be used as a replacement for a once lock after release (to reduce memory
  usage).
.. aiologic.lowlevel.THREAD_DUMMY_LOCK-end-marker

.. autofunction:: aiologic.lowlevel.create_thread_lock() -> ThreadLock
.. autofunction:: aiologic.lowlevel.create_thread_rlock() -> ThreadRLock
.. autofunction:: aiologic.lowlevel.create_thread_oncelock() -> ThreadOnceLock
.. autofunction:: aiologic.lowlevel.once

Queues (low-level)
++++++++++++++++++

.. aiologic.lowlevel.lazydeque-start-marker
.. class:: aiologic.lowlevel.lazydeque
  :no-index:

  Bases: :class:`MutableSequence[_T] <collections.abc.MutableSequence>`

  ...
.. aiologic.lowlevel.lazydeque-end-marker

.. aiologic.lowlevel.lazyqueue-start-marker
.. class:: aiologic.lowlevel.lazyqueue
  :no-index:

  Bases: :class:`Generic[_T] <typing.Generic>`

  ...
.. aiologic.lowlevel.lazyqueue-end-marker

Advanced topics
---------------

Libraries
+++++++++

.. autofunction:: aiologic.lowlevel.current_async_library
.. autofunction:: aiologic.lowlevel.current_green_library

.. aiologic.lowlevel.current_async_library_tlocal-start-marker
.. py:data:: aiologic.lowlevel.current_async_library_tlocal
  :type: threading.local
  :no-index:

  Thread-local data to control the return value of
  :func:`aiologic.lowlevel.current_async_library`.

  .. py:attribute:: aiologic.lowlevel.current_async_library_tlocal.name
    :type: str | None
    :value: None
    :no-index:

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
.. aiologic.lowlevel.current_async_library_tlocal-end-marker

.. aiologic.lowlevel.current_green_library_tlocal-start-marker
.. py:data:: aiologic.lowlevel.current_green_library_tlocal
  :type: threading.local
  :no-index:

  Thread-local data to control the return value of
  :func:`aiologic.lowlevel.current_green_library`.

  .. py:attribute:: aiologic.lowlevel.current_green_library_tlocal.name
    :type: str | None
    :value: None
    :no-index:

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
.. aiologic.lowlevel.current_green_library_tlocal-end-marker

.. aiologic.lowlevel.AsyncLibraryNotFoundError-start-marker
.. py:exception:: aiologic.lowlevel.AsyncLibraryNotFoundError
  :no-index:

  Bases: :exc:`RuntimeError`

  Exception raised by the :func:`aiologic.lowlevel.current_async_library`
  function if the current async library was not recognized.
.. aiologic.lowlevel.AsyncLibraryNotFoundError-end-marker

.. aiologic.lowlevel.GreenLibraryNotFoundError-start-marker
.. py:exception:: aiologic.lowlevel.GreenLibraryNotFoundError
  :no-index:

  Bases: :exc:`RuntimeError`

  Exception raised by the :func:`aiologic.lowlevel.current_green_library`
  function if the current green library was not recognized.
.. aiologic.lowlevel.GreenLibraryNotFoundError-end-marker

Execution units
+++++++++++++++

.. aiologic.lowlevel.current_thread-start-marker
.. py:function:: aiologic.lowlevel.current_thread() -> threading.Thread
  :no-index:

  ...
.. aiologic.lowlevel.current_thread-end-marker

.. aiologic.lowlevel.current_thread_ident-start-marker
.. py:function:: aiologic.lowlevel.current_thread_ident() -> int
  :no-index:

  ...
.. aiologic.lowlevel.current_thread_ident-end-marker

.. autofunction:: aiologic.lowlevel.current_async_token
.. autofunction:: aiologic.lowlevel.current_green_token
.. autofunction:: aiologic.lowlevel.current_async_token_ident
.. autofunction:: aiologic.lowlevel.current_green_token_ident
.. autofunction:: aiologic.lowlevel.current_async_task
.. autofunction:: aiologic.lowlevel.current_green_task
.. autofunction:: aiologic.lowlevel.current_async_task_ident
.. autofunction:: aiologic.lowlevel.current_green_task_ident

Cancellation and timeouts
+++++++++++++++++++++++++

.. autofunction:: aiologic.lowlevel.async_clock
.. autofunction:: aiologic.lowlevel.green_clock
.. autofunction:: aiologic.lowlevel.async_sleep
.. autofunction:: aiologic.lowlevel.green_sleep
.. autofunction:: aiologic.lowlevel.async_sleep_until
.. autofunction:: aiologic.lowlevel.green_sleep_until
.. autofunction:: aiologic.lowlevel.async_sleep_forever
.. autofunction:: aiologic.lowlevel.green_sleep_forever
.. autofunction:: aiologic.lowlevel.async_seconds_per_sleep
.. autofunction:: aiologic.lowlevel.green_seconds_per_sleep
.. autofunction:: aiologic.lowlevel.async_seconds_per_timeout
.. autofunction:: aiologic.lowlevel.green_seconds_per_timeout
.. autofunction:: aiologic.lowlevel.shield

Checkpoints and fairness
++++++++++++++++++++++++

.. autofunction:: aiologic.lowlevel.async_checkpoint
.. autofunction:: aiologic.lowlevel.green_checkpoint
.. autofunction:: aiologic.lowlevel.async_checkpoint_if_cancelled
.. autofunction:: aiologic.lowlevel.green_checkpoint_if_cancelled
.. autofunction:: aiologic.lowlevel.async_checkpoint_enabled
.. autofunction:: aiologic.lowlevel.green_checkpoint_enabled
.. autofunction:: aiologic.lowlevel.enable_checkpoints
.. autofunction:: aiologic.lowlevel.disable_checkpoints

Safety and reentrancy
+++++++++++++++++++++

.. autofunction:: aiologic.lowlevel.signal_safety_enabled
.. autofunction:: aiologic.lowlevel.enable_signal_safety
.. autofunction:: aiologic.lowlevel.disable_signal_safety

Metaprogramming
---------------

Singletons and markers
++++++++++++++++++++++

.. autoclass:: aiologic.meta.SingletonEnum
  :no-inherited-members:
.. autoclass:: aiologic.meta.DefaultType
  :no-inherited-members:
.. autoclass:: aiologic.meta.MissingType
  :no-inherited-members:

.. aiologic.meta.DEFAULT-start-marker
.. data:: aiologic.meta.DEFAULT
  :type: DefaultType
  :no-index:

  A singleton object for default values; mimics :data:`None`.

  Used as a marker to indicate that some object will be used by default
  (without any special behavior).
.. aiologic.meta.DEFAULT-end-marker

.. aiologic.meta.MISSING-start-marker
.. data:: aiologic.meta.MISSING
  :type: MissingType
  :no-index:

  A singleton object for default values; mimics :data:`None`.

  Used as a marker to indicate that some special behavior will be used by
  default (cannot be achieved by passing any value).

  Can also be used outside of parameters to indicate that there is no object.
.. aiologic.meta.MISSING-end-marker

Functions
+++++++++

.. autofunction:: aiologic.meta.replaces
.. autofunction:: aiologic.meta.copies

Modules
+++++++

.. autofunction:: aiologic.meta.resolve_name

Imports
+++++++

.. autofunction:: aiologic.meta.import_module
.. autofunction:: aiologic.meta.import_from

Exports
+++++++

.. autofunction:: aiologic.meta.export
.. autofunction:: aiologic.meta.export_dynamic
.. autofunction:: aiologic.meta.export_deprecated

Helpers
+++++++

.. autofunction:: aiologic.meta.await_for
