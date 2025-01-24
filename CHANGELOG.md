<!--
SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
SPDX-License-Identifier: CC-BY-4.0
-->

Changelog
=========

All notable changes to this project will be documented in this file.

The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Commit messages are consistent with
[Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).

[0.13.1] - 2025-01-24
---------------------

### Fixed

- Optimized the event removal in locks and semaphores. Previously, removing an
  event from the waiting queue was performed even when it was successfully set,
  which caused serious slowdown due to expensive O(n) operations.
  Now the removal is only performed in case of failure - on cancellation,
  in particular timeouts, and exceptions.
  ([#5](https://github.com/x42005e1f/aiologic/issues/5)).

[0.13.0] - 2025-01-19
---------------------

### Added

- Type annotations via stubs. They are tested via `mypy` and `pyright`, but may
  cause ambiguities in some IDEs that do not support overloading well.

### Changed

- The source code tree has been significantly changed for better IDEs support.
  The same applies to exports, which are now checker-friendly. Objects pickled
  in previous versions refer to the old tree, so aliases to old modules have
  been _temporarily_ added. If you have these, it is strongly recommended to
  repickle them with this version to support future versions.

[0.12.0] - 2024-12-14
---------------------

### Changed

- Support for cancellation and timeouts has been dramatically improved.
  The `cancel()` method (and accompanying `is_cancelled()`) has been added to
  low-level events, which always returns `True` after the first successful call
  before `set()` and `False` otherwise. Previously, cancellation handling used
  the same `set()` call, which resulted in false negatives, in particular
  unnecessary wakes.

### Fixed

- Added missing `await` keyword in `aiologic.Condition`, without which it did
  not restore the state of the wrapped `aiologic.RLock` (`0.11.0` regression).
- Priority queue initialization now ensures the heap invariant for the passed
  list. Previously, passing a list with an incorrect order of elements violated
  the order in which the priority queue elements were returned.
- Low-level event classes are now created in exclusive mode, eliminating
  possible slowdown in method resolution.

[0.11.0] - 2024-11-08
---------------------

### Added

- `aiologic.lowlevel.async_checkpoint()` as an alias for
  `aiologic.lowlevel.checkpoint()`.

### Changed

- The capabilities of `aiologic.Condition` have been extended. Since there is
  no clear definition of which locks it should wrap, support for sync-only
  locks such as `threading.Lock` has been added. Passing another instance of
  `aiologic.Condition` is now supported too, and implies copying a reference to
  its lock. Also, passing `None` now specifies a different behavior whereby
  `aiologic.Condition` acts as lockless: its methods ignore the lock, which
  should help to use `aiologic.Condition` as a simple replacement for removed
  `aiologic.ParkingLot`.

[0.10.0] - 2024-11-04
---------------------

### Changed

- `aiologic.lowlevel.shield()` function, which protects the call from
  cancellation, has been replaced by `aiologic.lowlevel.repeat_if_cancelled()`,
  which, depending on the library, either has the same action or repeats the
  call until it completes (successfully or unsuccessfully).
  Previously `anyio.CancelScope` was used, which did not really shield the call
  from cancellation in ways outside of `anyio`, such as `task.cancel()`, so its
  use was abandoned. However, `asyncio.shield()` starts a new task, which has a
  negative impact on performance and does not match the expected single-switch
  behavior. This is why repeat instead of shield was chosen. This change
  directly affects `aiologic.Condition`.

[0.9.0] - 2024-11-02
--------------------

### Changed

- `aiologic.CountdownEvent` is significantly improved. Instead of using the
  initial value for the representation, it now uses the current value, so that
  its state is saved when the `pickle` module is used, just like the other
  events. Also added the ability to increase the current value by more than one
  per call, which should help with performance in some scenarios.
  The new `clear()` method, which atomically resets the current value, has the
  same purpose.
- Changed the detection of the current green library after applying the monkey
  patch. Now the library that applied the patch is set only for the main
  thread, and the default library (usually `threading`) is used for all others.
  This should eliminate redundancy when using worker threads, which previously
  had to explicitly set `threading` to avoid accidentally creating a new hub
  and hence an event loop.

[0.8.1] - 2024-10-30
--------------------

### Fixed

- The future used by the `asyncio` event could be canceled due to the event
  loop shutdown, causing `InvalidStateError` to be raised due to the callback
  execution. In particular, this was detected when using `call_soon()`
  for notification methods.

[0.8.0] - 2024-10-26
--------------------

### Added

- `aiologic.CountdownEvent` as a countdown event, i.e. an event that wakes up
  all tasks when its value is down to zero (inspired by `CountdownEvent` from
  .NET Framework 4.0).
- `aiologic.RCapacityLimiter` as a reentrant version of
  `aiologic.CapacityLimiter`.

[0.7.1] - 2024-10-20
--------------------

### Fixed

- `aiologic.Condition` was referring to the wrong variable in its notification
  methods, which caused hangs (`0.2.0` regression).

[0.7.0] - 2024-10-19
--------------------

### Added

- `aiologic.Barrier` as a cyclic barrier, i.e. a barrier that tasks can pass
  through repeatedly (thread-aware alternative to `asyncio.Barrier`).
- `aiologic.SimpleQueue` as a simplified queue without `maxsize` support.
- `aiologic.PriorityQueue` as a priority queue, i.e. a queue that returns its
  smallest element (using the `heapq` module).

### Changed

- Once again the queues have been significantly changed. `aiologic.Queue` and
  its derivatives now use a unique architecture that guarantees exclusive
  access to inherited methods without increasing the number of context
  switches: implicit lock and wait queue are combined. Overridable methods are
  now part of the public API, and fairness now covers all accesses.
  The properties returning the length of waiting queues have also been changed:
  a common `waiting` property returning the number of all waiting ones has been
  added, and `put_waiting` and `get_waiting` have been renamed to `putting` and
  `getting`.

[0.6.0] - 2024-09-29
--------------------

### Added

- `force` parameter for green checkpoints (allowing to ignore context variables
  and environment variables).

### Fixed

- Added the missing `return` keyword in queue implementations, without which
  they always returned `None` in `green_get()` and `async_get()` methods
  (`0.4.0` regression).
- `aiologic.Latch` now preserves the original task order for greenlets.
  Previously, the last greenlet always passed the barrier first when
  checkpoints were disabled.

[0.5.0] - 2024-09-28
--------------------

### Added

- `aiologic.CapacityLimiter` as a primitive similar to `aiologic.Semaphore`,
  but with ownership checking on release like `aiologic.Lock`
  (thread-aware alternative to `anyio.CapacityLimiter`).
- `aiologic.Latch` as a single-use barrier, useful for ensuring that no thread
  or task sleeps after passing the barrier (inspired by `std::latch` from
  C++20).
- `force` parameter for async checkpoints (allowing to ignore context variables
  and environment variables).

[0.4.0] - 2024-09-23
--------------------

### Changed

- `aiologic.SimpleQueue` has been replaced by `aiologic.Queue` (FIFO) and
  `aiologic.LifoQueue` (LIFO) with the same performance. Unlike
  `aiologic.SimpleQueue`, they support `maxsize` and their methods have
  `green_` and `async_` prefixes, which follows the common naming convention.
  And since they have two different waiting queues, the `waiting` property has
  been replaced with `put_waiting` and `get_waiting`.
- The build system has been changed to `pyproject.toml`-only instead of
  `pyproject.toml` + `setup.cfg` + `setup.py`. It should be more trusted by new
  users, since it does not contain executable code.
  ([#1](https://github.com/x42005e1f/aiologic/pull/1)).

[0.3.0] - 2024-09-23
--------------------

### Added

- `weakref` support for all high-level primitives.

### Fixed

- In the implementation of asynchronous checkpoints, the `await` keyword was
  missing, causing the checkpoints to have no effect (`0.2.0` regression).
- In `aiologic.REvent`, woken tasks now inherit the timestamp of the one that
  woke them up, which eliminates false wakes in the `set()` + `clear()`
  scenario.
- The `setup.py` code has been simplified to avoid
  `SetuptoolsDeprecationWarning`.

[0.2.0] - 2024-09-10
--------------------

### Added

- `eventlet` and `gevent` support.
- `aiologic.PLock` as a primitive lock, i.e. the fastest exclusive lock that
  does not do checks in `release()` methods.
- `aiologic.REvent` as a reusable event, i.e. an event that supports the
  `clear()` method (async-aware alternative to `threading.Event`).
- `aiologic.ResourceGuard` for ensuring that a resource is only used by a
  single task at a time (thread-safe alternative to `anyio.ResourceGuard`).
- `release()` method to `aiologic.Semaphore` and `aiologic.BoundedSemaphore`.
- `max_value` parameter to `aiologic.Semaphore` to allow creating an instance
  of `aiologic.BoundedSemaphore` without importing it.
- `waiting` property to all primitives that returns the length of waiting queue
  (number of waiting threads and tasks).
- Non-blocking (non-waiting) mode for asynchronous lock acquiring methods.
  In this mode, it is guaranteed that there is no context switching even with
  checkpoints enabled (they are ignored). Unlike synchronous methods,
  lock acquiring is done on behalf of an asynchronous task. It is enabled by
  passing `blocking=False`.
- The ability to specify the library used via environment variables, local
  thread fields, context variables.
- Patch for the `threading` module that fixes the race in `Thread.join()` on
  PyPy. Automatically applied when creating an instance of the threading event.
- Patch for the `eventlet` module that adds the necessary methods to support
  it. Automatically applied when creating an instance of eventlet event.
- Optional dependencies to guarantee support for third-party libraries
  (by specifying the minimum supported version).

### Changed

- Checkpoints are now optional. They can be enabled or disabled via environment
  variables or context variables. They are enabled by default for Trio.
- `_as_thread` and `_as_task` suffixes are replaced by `green_` and `async_`
  prefixes. Other options were considered, but only such prefixes ensure that
  the two different APIs are equal in convenience.
- `aiologic.Lock` and `aiologic.RLock` no longer support upgrading from
  synchronous to asynchronous access, which avoids some issues in complex
  scenarios.
- `put()` and `aput()` methods in `aiologic.SimpleQueue` are replaced by the
  common `put()` method (without `blocking` and `timeout` parameters).
- `aiologic.SimpleQueue` now throws its own `aiologic.QueueEmpty` exception
  instead of `queue.Empty`.
- `aiologic.lowlevel.ThreadEvent` is renamed to `aiologic.lowlevel.GreenEvent`
  and `aiologic.lowlevel.TaskEvent` is renamed to
  `aiologic.lowlevel.AsyncEvent`.
- `set()` method of low-level events now returns `bool`: `True` if called
  for the first time, `False` otherwise.
- Identification functions are changed due to support for new libraries.
  `aiologic.lowlevel.current_thread()` now returns a `threading.Thread`
  instance instead of its identifier, and a new function
  `aiologic.lowlevel.current_thread_ident()` has been added to get the
  identifier instead. The old `aiologic.lowlevel.current_token()` and
  `aiologic.lowlevel.current_task()` are now differentiated by library type
  (`current_green_` and `current_async_`). Additional functions with the
  `_ident` suffix have also been added to get an identifier instead of an
  object.

### Removed

- `aiologic.ParkingLot`: now each primitive uses its own lightweight code to
  handle the waiting queue.
- `aiologic.lowlevel.AsyncioEvent` and `aiologic.lowlevel.TrioEvent`: they are
  now private.
- `aiologic.lowlevel.Flags.markers`: it is now private.

### Fixed

- In very rare cases, notification methods (`notify()`, `release()`, and so on)
  did not notify newcomers due to a race, causing a hang. Now they are fully
  thread-safe.
- `aiologic.Condition` now uses timestamps for wakeups, which provides expected
  behavior in complex scenarios (and eliminates resource starvation). The same
  is implemented in `aiologic.REvent`.
- The `threading` event now calls `lock.acquire(blocking=False)` instead of
  `lock.acquire(timeout=timeout)` on a negative timeout, which is consistent
  with the behavior of `threading.Event`.
- The `default_factory()` call in `aiologic.lowlevel.Flag.get()` is now
  performed outside the except block, which simplifies stack traces.
- Eager imports are replaced by lazy imports, so that only necessary ones are
  imported at runtime. This avoids some issues related to incompatibility of
  library versions.

[0.1.1] - 2024-08-08
--------------------

### Fixed

- `aiologic.ParkingLot` is now fair (and hence all other primitives too).

[0.1.0] - 2024-08-06
--------------------

Check back later!

[0.13.1]: https://github.com/x42005e1f/aiologic/compare/0.13.0...0.13.1
[0.13.0]: https://github.com/x42005e1f/aiologic/compare/0.12.0...0.13.0
[0.12.0]: https://github.com/x42005e1f/aiologic/compare/0.11.0...0.12.0
[0.11.0]: https://github.com/x42005e1f/aiologic/compare/0.10.0...0.11.0
[0.10.0]: https://github.com/x42005e1f/aiologic/compare/0.9.0...0.10.0
[0.9.0]: https://github.com/x42005e1f/aiologic/compare/0.8.1...0.9.0
[0.8.1]: https://github.com/x42005e1f/aiologic/compare/0.8.0...0.8.1
[0.8.0]: https://github.com/x42005e1f/aiologic/compare/0.7.1...0.8.0
[0.7.1]: https://github.com/x42005e1f/aiologic/compare/0.7.0...0.7.1
[0.7.0]: https://github.com/x42005e1f/aiologic/compare/0.6.0...0.7.0
[0.6.0]: https://github.com/x42005e1f/aiologic/compare/0.5.0...0.6.0
[0.5.0]: https://github.com/x42005e1f/aiologic/compare/0.4.0...0.5.0
[0.4.0]: https://github.com/x42005e1f/aiologic/compare/0.3.0...0.4.0
[0.3.0]: https://github.com/x42005e1f/aiologic/compare/0.2.0...0.3.0
[0.2.0]: https://github.com/x42005e1f/aiologic/releases/tag/0.2.0
[0.1.1]: https://pypi.org/project/aiologic/0.1.1/
[0.1.0]: https://pypi.org/project/aiologic/0.1.0/
