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
