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

[Unreleased]
------------

### Added

- `aiologic.BLock` as a bounded lock (async-aware alternative to
  `threading.Lock`).
- `aiologic.lowlevel.enable_checkpoints()` and
  `aiologic.lowlevel.disable_checkpoints()` universal decorators to enable and
  disable checkpoints in the current thread's context. They support awaitable
  objects, coroutine functions, and green functions, and can be used directly
  as context managers.
- `aiologic.lowlevel.green_checkpoint_enabled()` and
  `aiologic.lowlevel.async_checkpoint_enabled()` to determine if checkpoints
  are enabled for the current library.
- `aiologic.lowlevel.green_checkpoint_if_cancelled()` and
  `aiologic.lowlevel.async_checkpoint_if_cancelled()`. Currently,
  `aiologic.lowlevel.async_checkpoint_if_cancelled()` is equivalent to removed
  `aiologic.lowlevel.checkpoint_if_cancelled()`, and
  `aiologic.lowlevel.green_checkpoint_if_cancelled()` does nothing. However,
  these methods have a slightly different meaning: they are intended to
  accompany `aiologic.lowlevel.shield()` calls to pre-check for cancellation,
  and do not guarantee actual checking.
- `green_owned()` and `async_owned()` methods to ownable and reentrant locks.
  They allow to check if the lock is owned by the current task without
  importing additional functions.
- Reentrant locks can now be acquired and released multiple times in a single
  call.
- `for_()` method to condition variables as an async analog of `wait_for()`.
- Conditional variables now support user-defined timers. They can be passed to
  the constructor, called via the `timer` property, and used to pass the
  deadline to the notification methods.
- Low-level events can now be shielded from external cancellation by passing
  `shield=True`. This allows to implement efficient finalization strategies
  while preserving the one-time nature of low-level events.
- Low-level events can now be forced (like checkpoints) by passing
  `force=True`. This allows to use existing event objects instead of
  checkpoints to minimize possible overhead.
- `aiologic.lowlevel.SET_EVENT` and `aiologic.lowlevel.CANCELLED_EVENT` as
  variants of `aiologic.lowlevel.DUMMY_EVENT` for a set event and a cancelled
  event respectively. In fact, `aiologic.lowlevel.SET_EVENT` is just a copy of
  `aiologic.lowlevel.DUMMY_EVENT`, but to avoid confusion both variants will
  coexist (maybe temporarily, maybe not).
- `AIOLOGIC_GREEN_CHECKPOINTS` and `AIOLOGIC_ASYNC_CHECKPOINTS` environment
  variables.

### Changed

- Reentrant primitives now have checkpoints on reentrant acquires. This should
  make their behavior more predictable. Previously, checkpoints were not called
  if a primitive had already been acquired (for performance reasons).
- Checkpoints have been rewritten:
  + `aiologic.lowlevel.repeat_if_cancelled()` has been replaced by
    `aiologic.lowlevel.shield()`. Unlike the pre-0.10.0 function of the same
    name, it is now a universal decorator, and it combines both semantics: it
    shields both the called function and the calling task from being cancelled.
    It supports awaitable objects, coroutine functions, and green functions:
    timeouts are suppressed, and are re-raised after the call completes.
  + They now skip the current library detection if they have not been enabled
    for any imported libraries. This also affects checkpoints in low-level
    events, which no longer access context variables before enabling
    checkpoints, making them much faster.
  + They can now only be enabled dynamically (without environment variables) at
    the thread level. This prevents checkpoints from being enabled in created
    worker threads.
- Low-level events have been rewritten:
  + `event.is_cancelled()` has been renamed to `event.cancelled()`. This makes
    them more similar to `asyncio` futures and thus more familiar to new users.
  + They are now always cancelled on timeouts, and the `event.cancel()` method
    has been removed to avoid redundancy. This should make it easier to work
    with them outside of `aiologic` and simplify some things, since now there
    is no need to call `event.cancel()`. Previously, green events were not
    cancelled when a timeout was passed.
  + They are no longer considered set after being cancelled. This affects the
    return value of `bool(event)` and `event.is_set()`, which now return
    `False` for cancelled events.
  + They now return `False` after waiting again if they were previously
    cancelled. Previously `True` was returned, which could be considered
    unexpected behavior.
  + Their performance has been greatly improved. Checkpoints now use their own
    implementation without calling public `aiologic.lowlevel` functions, which
    bypasses redundant current library detection. The `gevent` events have been
    rewritten to be similar to the `eventlet` events, making them faster than
    the native `gevent` events.
  + They are now bound to the event loop in the wait function rather than in
    the event constructor (there is also an option to defer library detection
    to the wait function by introducing a new abstraction (waiters) and adding
    a generic `aiologic.lowlevel.AnyEvent`, but this has a negative impact on
    memory, and the performance gain for high-level primitives is only in the
    race condition).
- Condition variables have been rewritten:
  + They now only support passing locks from the `threading` module
    (synchronous mode), locks from the `aiologic` module (mixed mode), and
    `None` (lockless mode). This change was made to simplify their
    implementation. For special cases it is recommended to use low-level events
    directly.
  + They now count the number of lock acquires to avoid redundant `release()`
    calls when used as context managers. Because of this, they will now never
    throw a `RuntimeError` when a `wait()` call fails (e.g. due to a
    `KeyboardInterrupt` while trying to reacquire `threading.Lock`). This makes
    it safe (with some caveats) to use condition variables even when shielding
    from external cancellation is not guaranteed.
  + They now shield lock state restoring not only in async methods, but also in
    green methods. It is still not guaranteed that a `wait()` call cannot be
    cancelled in any unpredictable way (e.g. when a greenlet is killed by an
    exception other than `GreenletExit`), but now condition variables can be
    safely used in more scenarios.
  + They now check that the current task is the owner of the lock before
    starting the wait. This corresponds to the behavior of the standard
    condition variables, and allows exceptions to be raised with more
    meaningful messages.
  + They now return the original value of the predicate, allowing the
    `wait_for()` and `for_()` methods to be used in more scenarios. Previously,
    a value of type `bool` was returned.
  + They are now more accurately interpreted as `bool`. For locks from the
    `threading` module, `True` is returned if the lock is locked and `False`
    otherwise, which matches the behavior of locks from the `aiologic` module.
    For `None`, `False` is always returned. With this change, condition
    variables can now be used to determine the status of an operation (just
    like normal `aiologic` locks) regardless of the lock used. Previously,
    `True` was always returned for both cases.
- The representation of primitives has been changed. All instances now include
  the module name and use the correct class name in subclasses (except for
  private classes). Low-level events now show their library identity and status
  in representation.
- `aiologic.lowlevel.current_green_token()` now returns the current thread, and
  `aiologic.lowlevel.current_green_token_ident()` now uses the current thread
  ID for `threading`. This makes these functions more meaningful, and leads to
  the expected behavior in group-level locks. Previously, constant values were
  returned for `threading`.
- `sniffio` is now a required dependency. This is done to simplify the code
  logic (which previously treated `sniffio` as an optional dependency) and
  should not introduce any additional complexity.
- `typing-extensions` is now a required dependency on Python < 3.13. This is
  done to make it easier to work with stubs and use new features (such as
  `warnings.deprecated`) on older versions of Python.
- The build system has been changed from `setuptools` to `uv` + `hatch`. It
  keeps the same `pyproject.toml` format, but has better performance, better
  logging, and builds cleaner source distributions (without `setup.cfg`).
  Dependencies specific to the development process have been redefined using
  [PEP 735](https://peps.python.org/pep-0735/).
- The version identifier is now generated dynamically and includes the latest
  commit information for development versions, which simplifies bug reporting.
  It is also passed to archives generated by GitHub (via `.git_archival.txt`)
  and source distributions (via `PKG-INFO`).

### Deprecated

- `aiologic.lowlevel.checkpoint()` in favor of
  `aiologic.lowlevel.async_checkpoint()` (previously alias): checkpoints are
  now strictly separated into green and async checkpoints.

### Removed

- `aiologic.lowlevel.<library>_running()`: these functions have not been used
  and could be misleading.
- `aiologic.lowlevel.checkpoint_if_cancelled()` and
  `aiologic.lowlevel.cancel_shielded_checkpoint()`: they only supported
  asynchronous libraries and were not actually used in high-level primitives.
- `aiologic.lowlevel.<library>_checkpoints_cvar` in favor of
  `aiologic.lowlevel.enable_checkpoints()` and
  `aiologic.lowlevel.disable_checkpoints()`.
- `AIOLOGIC_GREEN_LIBRARY` and `AIOLOGIC_ASYNC_LIBRARY` environment variables:
  they could be confusing because they did not affect
  `sniffio.current_async_library()`. The alternative of setting the default
  directly in `sniffio` (via `sniffio.thread_local.__class__.name`) affects
  `anyio`, which refuses to make a successful `anyio.run()` call when the
  current async library is set.

### Fixed

- In `aiologic.lowlevel.shield()` (previously
  `aiologic.lowlevel.repeat_if_cancelled()`):
  + Hangs could occur when using `anyio.CancelScope()` with the `asyncio`
    backend. Now this case is handled in a special way. Related:
    [agronholm/anyio#884](https://github.com/agronholm/anyio/issues/884).
  + Reference cycles were possible when another exception was raised after a
    `asyncio.CancelledError` was caught: in this case, the last
    `asyncio.CancelledError` was not removed from the frame.
- Using checkpoints for `threading` could cause hub spawning in worker threads
  when `aiologic` is imported after monkey patching the `time` module with
  `eventlet` or `gevent`. As a result, the open files limit could have been
  exceeded.
- The locks and semaphores (and the capacity limiters and simple queues based
  on them) did not handle exceptions at checkpoints, so that cancelling at
  checkpoints (`trio` case by default) did not release the primitive.
- The methods of complex queues (all except `aiologic.SimpleQueue`) used an
  incorrect condition for cancellation handling, which could break
  thread-safety after cancellation. Now the handling is changed to match that
  of locks and semaphores, which additionally speeds up methods by reducing
  operations.
- In very rare cases, `curio` events would set the future attribute after the
  `set()` method was completed and thus cause a hang.
- In very rare cases, lock acquiring methods did not notify newcomers due to
  calling a non-existent method when racing during cancellation, causing a hang
  (`0.14.0` regression).
- A non-existent function was imported for `trio` tokens, which resulted in
  inability to use `aiologic.lowlevel.current_async_token()` and
  `aiologic.lowlevel.current_async_token_ident()` for `trio` (`0.14.0`
  regression).
- The `_local` class was imported directly from the `_thread` module, which
  caused the current library to be set only for the current greenlet and not
  for the whole thread after monkey patching (`0.14.0` regression).
- Semaphores with value > 1 incorrectly handled the optimistic acquire case
  after adding an event to the queue, resulting in excessive decrements in a
  free-threading mode (`0.2.0` regression).

[0.14.0] - 2025-02-12
---------------------

### Added

- Experimental `curio` support.

### Changed

- Support for libraries has been redefined with `wrapt` via post import hooks.
  Previously, available libraries were determined after the first use, which
  could lead to unexpected behavior in interactive scenarios. Now support for a
  library is activated when the corresponding library is imported.
- Support for greenlet-based libraries has been simplified. Detecting the
  current green library is now done by hub: if any `eventlet` or `gevent`
  function was called in the current thread, the current thread starts using
  the corresponding library. This eliminates the need to specify a green
  library both before and after monkey patching.
- Corrected type annotations:
  + `aiologic.BoundedSemaphore` extends `aiologic.Semaphore`, and
    `aiologic.Semaphore` returns an instance of `aiologic.BoundedSemaphore`
    when passing `max_value`. Previously, the classes were independent in
    stubs, which was inconsistent with the behavior added in `0.2.0`.
  + `aiologic.lowlevel.current_thread()` returns `Optional[threading.Thread]`.
    Previously, `threading.Thread` was returned, which was inconsistent with
    the special handling of `threading._DummyThread`.

### Removed

- Aliases to old modules (affects objects pickled before `0.13.0`).
- Patcher-related exports (such as `aiologic.lowlevel.start_new_thread()`).
- `aiologic.lowlevel.current_async_library_cvar`: the `sniffio` equivalent is
  deprecated and not used by modern libraries, and the performance impact of
  using it is only negative.

### Fixed

- `asyncio` was not considered running when the current task was `None`. This
  resulted in the inability to use any async functions in
  [asyncio REPR](https://docs.python.org/3/library/asyncio.html#asyncio-cli)
  without explicitly setting the current async library. Related:
  [python-trio/sniffio#35](https://github.com/python-trio/sniffio/issues/35).
- There was a missing branch for the optimistic case of non-waiting lock
  acquiring during race condition, which caused hangs in a free-threaded mode
  (`0.13.1` regression).

[0.13.1] - 2025-01-24
---------------------

### Fixed

- Optimized the event removal in locks and semaphores. Previously, removing an
  event from the waiting queue was performed even when it was successfully set,
  which caused serious slowdown due to expensive O(n) operations. Now the
  removal is only performed in case of failure - on cancellation, in particular
  timeouts, and exceptions.
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

- Support for cancellation and timeouts has been dramatically improved. The
  `cancel()` method (and accompanying `is_cancelled()`) has been added to
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
  call until it completes (successfully or unsuccessfully). Previously
  `anyio.CancelScope` was used, which did not really shield the call from
  cancellation in ways outside of `anyio`, such as `task.cancel()`, so its use
  was abandoned. However, `asyncio.shield()` starts a new task, which has a
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
  per call, which should help with performance in some scenarios. The new
  `clear()` method, which atomically resets the current value, has the same
  purpose.
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
  execution. In particular, this was detected when using `call_soon()` for
  notification methods.

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
  now part of the public API, and fairness now covers all accesses. The
  properties returning the length of waiting queues have also been changed: a
  common `waiting` property returning the number of all waiting ones has been
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
  but with ownership checking on release like `aiologic.Lock` (thread-aware
  alternative to `anyio.CapacityLimiter`).
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
- Non-blocking (non-waiting) mode for asynchronous lock acquiring methods. In
  this mode, it is guaranteed that there is no context switching even with
  checkpoints enabled (they are ignored). Unlike synchronous methods, lock
  acquiring is done on behalf of an asynchronous task. It is enabled by passing
  `blocking=False`.
- The ability to specify the library used via environment variables, local
  thread fields, context variables.
- Patch for the `threading` module that fixes the race in `Thread.join()` on
  PyPy. Automatically applied when creating an instance of the threading event.
- Patch for the `eventlet` module that adds the necessary methods to support
  it. Automatically applied when creating an instance of eventlet event.
- Optional dependencies to guarantee support for third-party libraries (by
  specifying the minimum supported version).

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
- `set()` method of low-level events now returns `bool`: `True` if called for
  the first time, `False` otherwise.
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

### Added

- A mixed build system (`setup.py` + `setup.cfg` + `pyproject.toml`): supports
  both direct (via `setup.py`) and indirect (via `build` + `pip`) installation.
- Low-level functions:
  + `sniffio`-like `aiologic.lowlevel.current_async_library()` function.
  + `anyio`-like `aiologic.lowlevel.checkpoint()` function.
  + `anyio`-like `aiologic.lowlevel.checkpoint_if_cancelled()` function.
  + `anyio`-like `aiologic.lowlevel.cancel_shielded_checkpoint()` function.
  + `aiologic.lowlevel.current_thread()` to get the current thread identifier.
  + `aiologic.lowlevel.current_token()` to get the current async token.
  + `aiologic.lowlevel.current_task()` to get the current async task.
- Low-level primitives:
  + `aiologic.lowlevel.Flag` as a one-slot alternative to `dict.setdefault()`.
  + `aiologic.lowlevel.TaskEvent` as a thread-safe async event.
  + `aiologic.lowlevel.ThreadEvent` as a one-time thread event.
- Synchronization primitives:
  + `aiologic.ParkingLot` as a waiting queue for all other primitives (inspired
    by `trio.lowlevel.ParkingLot`).
  + `aiologic.Semaphore` as a async-aware alternative to `threading.Semaphore`.
  + `aiologic.BoundedSemaphore` as a async-aware alternative to
    `threading.BoundedSemaphore`.
  + `aiologic.Lock` as a thread-aware alternative to `anyio.Lock`.
  + `aiologic.RLock` as a async-aware alternative to `threading.RLock`.
  + `aiologic.Condition` as a async-aware alternative to `threading.Condition`.
  + `aiologic.Event` as a thread-aware alternative to `asyncio.Event`.
- Communication primitives:
  + `aiologic.SimpleQueue` as a queue that works in a semaphore style
    (async-aware alternative to `queue.SimpleQueue`).

[unreleased]: https://github.com/x42005e1f/aiologic/compare/0.14.0...HEAD
[0.14.0]: https://github.com/x42005e1f/aiologic/compare/0.13.1...0.14.0
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
