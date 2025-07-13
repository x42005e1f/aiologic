..
  SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
  SPDX-License-Identifier: CC-BY-4.0

Execution units
===============

Different concurrency libraries operate with different units of execution.
Using :func:`gevent.spawn`, you create greenlets. Using
:meth:`trio.Nursery.start_soon`, you create child tasks. Each of these runs
inside a thread, an even more generic unit of execution. By providing a common
interface for such different libraries, aiologic needs to clearly distinguish
between the different units of execution and at the same time choose at which
level the primitives will operate.
