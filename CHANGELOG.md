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

[0.16.0] - 2025-11-27
---------------------

### Added

- `aiologic.__version__` and `aiologic.__version_tuple__` as a way to retrieve
  the package version at runtime.
- `aiologic.meta.SingletonEnum` as a base class that encapsulates common logic
  of all type-checker-friendly singleton classes (such as
  `aiologic.meta.DefaultType` and `aiologic.meta.MissingType`).
- `aiologic.meta.resolve_name()` as an alternative to
  `importlib.util.resolve_name()` with more consistent behavior.
- `aiologic.meta.import_module()` as an alternative to
  `importlib.import_module()` with more consistent behavior.
- `aiologic.meta.import_from()` as a way to import attributes from modules. It
  differs from more naive solutions in that it raises an `ImportError` instead
  of an `AttributeError`, while not allowing names like `*`, and also in that
  it attempts to import submodules to achieve the expected behavior.
- `aiologic.meta.export_dynamic()` as an alternative to
  `aiologic.meta.export_deprecated()` that does not raise a
  `DeprecationWarning`. Useful for optional features that may be missing at
  runtime but should be available at the package level.
- `aiologic.meta.export()` and `aiologic.meta.export_deprecated()` now support
  passing module objects, which should simplify their use for manually created
  module objects.
- Final classes from `aiologic.meta` now support runtime introspection via the
  `__final__` attribute on all supported versions of Python.

### Changed

- `aiologic.meta.export()` has been redesigned:
  + It now updates not only the `__module__` attribute, but also name-related
    attributes. This provides the expected representation in cases where
    functions are created dynamically in a different context with a different
    name.
  + Attributes are only updated if the object type matches one of the supported
    types, which protects against undefined behavior due to problematic types
    (such as singletons that provide a read-only `__module__` attribute).
  + When a class is encountered, its members are also updated (recursively).
    This allows its functions to be referenced safely. In addition, properties
    and class/static methods are now also processed.
  + All non-public attributes are now skipped, which should reduce the number
    of operations performed.
  + For each package, it now builds a human-readable `__all__`, which gives the
    expected behavior of `from package import *` (in particular, public
    subpackages are now excluded) and also simplifies analysis.
- `aiologic.meta.export_deprecated()` now does additional checks before
  registering a link, and also relies on the new `importlib`-like functions,
  which should make it safer to use.
- Non-public functions for importing original objects now implement
  `aiologic.meta.import_from()`-like behavior, making them more predictable
  (relevant for a green-patched world).
- `aiologic.Queue` and its derivatives now raise a `ValueError` when attempting
  to pass a `maxsize` less than 1.
- All timeouts now raise a `ValueError` for values less than zero.

### Removed

- All deprecated features (see `0.15.0`).

### Fixed

- `aiologic.meta.replaces()` performed replacement by the name of the replaced
  function, which could lead to replacing an arbitrary object in the case of a
  different `__name__` attribute value.
- `aiologic.meta.replaces()` did not handle cases of parallel application to
  the same function, which could lead to an `AttributeError` being raised in
  such cases.
- `aiologic.meta.copies()` used a function copying technique that was
  incompatible with [Nuitka](https://github.com/Nuitka/Nuitka), resulting in a
  `RuntimeError` when attempting to call the copied function after compilation.
- `aiologic.meta.copies()` used the default keyword argument values of the
  replaced function, which could lead to unexpected behavior when the default
  values were different.

[0.15.0] - 2025-11-05
---------------------

### Added

- `aiologic.synchronized()` as an async-aware alternative to
  `wrapt.synchronized()`. Related: [GrahamDumpleton/wrapt#236](
  https://github.com/GrahamDumpleton/wrapt/issues/236).
- `aiologic.SimpleLifoQueue` as a simplified LIFO queue, i.e. a lightweight
  alternative to `aiologic.LifoQueue` without `maxsize` support.
- `aiologic.BinarySemaphore` and `aiologic.BoundedBinarySemaphore` as binary
  semaphores, i.e. semaphores restricted to the values 0 and 1 and using a more
  efficient implementation.
- `aiologic.RBarrier` as a reusable barrier, i.e. a barrier that can be reset
  to its initial state (async-aware alternative to `threading.Barrier`).
- `aiologic.lowlevel.ThreadLock` class (for typing purposes) and
  `aiologic.lowlevel.create_thread_lock()` factory function as a new way to
  obtain unpatched `threading.Lock`.
- `aiologic.lowlevel.ThreadRLock` class (for typing purposes) and
  `aiologic.lowlevel.create_thread_rlock()` factory function as a unique way to
  obtain unpatched `threading.RLock`. Solves the problem of using reentrant
  thread-level locks in the gevent-patched world (due to the fact that
  `threading._PyRLock.__globals__` referenced the patched namespace, which made
  it impossible to use the original object because it used the patched
  `threading.Lock`). Note: like `threading._PyRLock`, the fallback pure Python
  implementation is not signal-safe.
- `aiologic.lowlevel.ThreadOnceLock` class (for typing purposes) and
  `aiologic.lowlevel.create_thread_oncelock()` factory function as a way to
  obtain a one-time reentrant lock. The interface mimics that of
  `aiologic.lowlevel.ThreadRLock`, but the semantics are different: the first
  successful `release()` call, which sets the internal counter to zero, wakes
  up all threads at once (just like `aiologic.Event`), and all further
  `acquire()` calls become no-ops, which effectively turns the lock into a
  dummy primitive. And unlike `aiologic.lowlevel.ThreadRLock`, this primitive
  is signal-safe, which, combined with the described semantics, makes the
  primitive suitable for protecting initialization sections.
- `aiologic.lowlevel.ThreadDummyLock` class (for typing purposes) and
  `aiologic.lowlevel.THREAD_DUMMY_LOCK` singleton object as a way to obtain a
  dummy lock.
- `aiologic.lowlevel.once` decorator to ensure that a function is executed only
  once (inspired by `std::sync::Once` from Rust). It uses
  `aiologic.lowlevel.ThreadOnceLock` under the hood and stores the result in
  the wrapper's closure, which makes the function both thread-safe and
  signal-safe when `reentrant=True` is passed (note: this does not apply to
  side effects!).
- `aiologic.lowlevel.lazydeque` as a thread-safe/signal-safe wrapper for
  `collections.deque` with lazy initialization. It solves the problem of
  deques' high memory usage: one empty instance of `collections.deque` takes up
  760 bytes on Python 3.11+ (for comparison, one empty list takes up only 56
  bytes!). In contrast, one empty instance of `aiologic.lowlevel.lazydeque`
  takes up 128 bytes in total, and after initialization (first addition) takes
  up 832 bytes on Python 3.11+. Free-threading adds an additional 16 bytes in
  all cases (due to the internal use of `aiologic.lowlevel.ThreadOnceLock`).
- `aiologic.lowlevel.lazyqueue` as a thread-safe/signal-safe wrapper for
  `_queue.SimpleQueue` (when available) or `collections.deque` with lazy
  initialization. It provides a non-blocking queue and differs from
  `aiologic.lowlevel.lazydeque` in that it is more memory efficient at the cost
  of less functionality. Instead of 128 and 832 bytes, it takes up 120 and 200
  bytes on Python 3.13+.
- `aiologic.lowlevel.create_green_waiter()` and
  `aiologic.lowlevel.create_async_waiter()` as functions to create waiters,
  i.e. new low-level primitives that encapsulate library-specific wait-wake
  logic. Unlike low-level events, they have no state, and thus have less
  efficiency for multiple notifications (in particular, they schedule calls
  regardless of whether the wait has been completed or not). And, of course,
  for the same reason, they are even less safe (they require more specific
  conditions for their correct operation).
- `aiologic.lowlevel.enable_signal_safety()` and
  `aiologic.lowlevel.disable_signal_safety()` universal decorators to enable
  and disable signal-safety in the current thread's context. They support
  awaitable objects, coroutine functions, and green functions, and can be used
  directly as context managers.
- `aiologic.lowlevel.signal_safety_enabled()` to determine if signal-safety is
  enabled.
- `aiologic.lowlevel.create_green_event()` and
  `aiologic.lowlevel.create_async_event()` as a new way to create low-level
  events.
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
- `aiologic.lowlevel.green_clock()` and `aiologic.lowlevel.async_clock()` as a
  way to get the current time according to the current library's internal
  monotonic clock (useful for sleep-until functions).
- `aiologic.lowlevel.green_sleep()` and `aiologic.lowlevel.async_sleep()` to
  suspend the current task for the given number of seconds.
- `aiologic.lowlevel.green_sleep_until()` and
  `aiologic.lowlevel.async_sleep_until()` to suspend the current task until the
  given deadline (relative to the current library's internal monotonic clock).
- `aiologic.lowlevel.green_sleep_forever()` and
  `aiologic.lowlevel.async_sleep_forever()` to suspend the current task until
  an exception occurs.
- `aiologic.lowlevel.green_seconds_per_sleep()` and
  `aiologic.lowlevel.async_seconds_per_sleep()` as a way to get the number of
  seconds during which sleep guarantees exactly one checkpoint. If sleep
  exceeds this time, it will use multiple calls (to bypass library
  limitations).
- `aiologic.lowlevel.green_seconds_per_timeout()` and
  `aiologic.lowlevel.async_seconds_per_timeout()` that are the same as their
  sleep equivalents, but for timeouts (applies to low-level waiters/events, as
  well as all high-level primitives).
- `copy()` method to flags and queues as a way to create a shallow copy without
  additional imports.
- `async_borrowed()` and `green_borrowed()` methods to capacity limiters,
  `green_owned()` and `async_owned()` methods to locks. They allow to reliably
  check if the current task is holding the primitive (or any of its tokens)
  without importing additional functions.
- `async_count()` and `green_count()` to reentrant primitives for the same
  purpose, but returning how many releases need to be made before the primitive
  is actually released by the current task.
- Reentrant primitives can now be acquired and released multiple times in a
  single call.
- Multi-use barriers (cyclic and reusable) can now be used as context managers,
  which simplifies error handling.
- `for_()` method to condition variables as an async analog of `wait_for()`.
- Conditional variables now support user-defined timers. They can be passed to
  the constructor, called via the `timer` property, and used to pass the
  deadline to the notification methods.
- Low-level events can now support `aiologic.lowlevel.ThreadOnceLock` methods
  by passing `locking=True`. This allows to synchronize related one-time
  operations with less memory overhead.
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
- `aiologic.meta` subpackage for metaprogramming purposes.
- `aiologic.meta.MISSING` as a marker for parameters that, when not passed,
  specify special default behavior.
- `aiologic.meta.DEFAULT` as a marker for parameters with default values.
- `aiologic.meta.copies()` to replace a function with a copy of another.
- `aiologic.meta.replaces()` to replace a function of the same name in a
  certain namespace.
- `aiologic.meta.export()` to export all module content on behalf of the module
  itself (by updating `__module__`).
- `aiologic.meta.export_deprecated()` to export deprecated content via custom
  `__getattr__()`.
- `aiologic.meta.await_for()` to use awaitable primitives via functions that
  only accept asynchronous functions.
- `AIOLOGIC_GREEN_CHECKPOINTS` and `AIOLOGIC_ASYNC_CHECKPOINTS` environment
  variables.
- `AIOLOGIC_PERFECT_FAIRNESS` environment variable.

### Changed

- In previous versions, `aiologic` implicitly provided a strong fairness
  guarantee, informally called "perfect fairness". The point of this guarantee
  is to ensure the fairness of wakeups when they are parallel in nature. This
  had strong effects such as resuming all threads at once (no one is sleeping)
  on barrier wakeups and deterministic callback scheduling order in event loops
  when multiple threads call `release()` at the same time. This behavior is now
  explicit, optional, and disabled by default when GIL is also disabled. The
  reason for this change is that the behavior was not efficiently implemented
  at the Python level via existing atomic operations: `deque.remove()`
  increases worst-case time complexity from linear to cubic and gives a
  noticeable overhead that, in particular, makes barriers significantly slower
  with a huge number of threads in the free-threaded mode. Nevertheless, with
  implementation flaws, "perfect fairness" can still be useful, so since this
  version `aiologic` provides the `AIOLOGIC_PERFECT_FAIRNESS` environment
  variable to explicitly enable or disable it.
- To avoid cubic complexity, token removal in perfect fairness style (cannot be
  disabled in: multi-time events, multi-use barriers, and condition variables)
  is now synchronized via `aiologic.lowlevel.ThreadOnceLock` methods in the
  free-threaded mode.
- Signal-safety is now also explicit and can be configured via the universal
  decorators. When enabled, code behaves as if it were running outside the
  context in the same thread (as in a separate thread but with the same thread
  identifiers), allowing both notifying and waiting to be performed safely from
  inside signal handlers and destructors (affects library detection and
  low-level waiters).
- All timeouts now support the full range of int and float values, and
  correctly handle NaN and infinity (in particular, `timeout=inf` is equivalent
  to `timeout=None`). A side effect is that large timeouts (exceeding the
  maximum) increase the number of checkpoints.
- All primitives now use `aiologic.lowlevel.lazydeque` instead of
  `collections.deque` to reduce memory usage. This makes their memory usage a
  bit closer to `asyncio` primitives (more lightweight than some `threading`
  primitives!), and especially affects complex queues, which now consume only
  ~0.5 KiB instead of ~3 KiB per instance. But the cost of this is
  synchronization via `aiologic.lowlevel.ThreadOnceLock` at the first addition
  to the queue in free-threading.
- Shallow copying now relies on the `__copy__()` method instead of pickle
  methods. This makes copying faster at the cost of additional overriding in
  subclasses.
- Flags are now a high-level primitive, available as `aiologic.Flag`, with
  `weakref` support.
- Reentrant primitives now have checkpoints on reentrant acquires. This should
  make their behavior more predictable. Previously, checkpoints were not called
  if a primitive had already been acquired (for performance reasons).
- Interfaces and type hints have been improved:
  + Queues, capacity limiters, and flags are now generic types not only in
    stubs but also at runtime, making it possible to use subscriptions on
    Python 3.8. Also, capacity limiters' and flags' type parameters now have
    default values.
  + The use of markers as default parameter values has been expanded. `None` is
    used when it disables a particular feature (e.g. timeouts or maxsize).
    `aiologic.meta.MISSING` is used when it specifies a special default
    behavior. `aiologic.meta.DEFAULT` is used when an existing value that is
    compatible in type will be taken.
  + `aiologic.lowlevel.Event` is now a protocol not only in stubs but also at
    runtime.
  + Calling `flag.set()` without arguments is now only allowed for
    `aiologic.lowlevel.Flag[object]`. Previously it ignored subscriptions.
  + `aiologic.meta.MissingType` is now a subclass of `enum.Enum`, so static
    analysis tools now correctly recognize `aiologic.meta.MISSING` as a
    singleton instance.
  + `aiologic.lowlevel.current_green_library()` and
    `aiologic.lowlevel.current_async_library()` now return `Optional[str]` when
    passing `fallback=True`. Previously, `str` was returned, which was not the
    expected behavior.
  + `aiologic.lowlevel.AsyncLibraryNotFoundError` and
    `aiologic.lowlevel.current_async_library_tlocal` are now exactly the same
    as `sniffio.AsyncLibraryNotFoundError` and `sniffio.thread_local`. This
    allows them to be used interchangeably.
  + In all modules, type information is now also inline. This allows such
    information to be used in cases where stubs are not supported. In
    particular, for `sphinx.ext.autodoc`. Stubs are still preserved to reduce
    issues with type checkers.
  + Overload introspection is now available at runtime on all supported
    versions of Python.
- Thread-related functions have been rewritten:
  + `aiologic.lowlevel.current_thread()` now raises `RuntimeError` for threads
    started outside of the `threading` module instead of returning `None`. This
    is to prevent situations where the function is used for identification
    without proper handling of dummy threads, since in such cases dummy threads
    would share the same "identifier" - `None`.
  + The fallback `_thread._local` implementation now works not only with thread
    objects but also with main greenlet objects, so it now supports `gevent`'s
    pool of native worker threads.
- Checkpoints have been rewritten:
  + `aiologic.lowlevel.repeat_if_cancelled()` has been replaced by
    `aiologic.lowlevel.shield()`. Unlike the pre-0.10.0 function of the same
    name, it is now a universal decorator, and it combines both semantics: it
    shields both the called function and the calling task from being cancelled.
    It supports awaitable objects, coroutine functions, and green functions:
    timeouts are suppressed, and are re-raised after the call completes.
  + `threading` checkpoints now use `os.sched_yield()` (when available) as a
    way to quickly switch the GIL. This makes them cheaper, but may slightly
    alter their behavior in free-threading.
  + They now skip the current library detection when it is not required (for
    example, when checkpoints are not enabled for any of the imported
    libraries). This also affects checkpoints in low-level events, which no
    longer access context variables before using checkpoints, making them much
    faster.
  + They can now only be enabled dynamically (without environment variables) at
    the thread level. This prevents checkpoints from being enabled in created
    worker threads.
- Low-level events have been rewritten:
  + They are now built on waiters (new low-level primitives), due to which they
    determine the current library and access the specific API only in wait
    methods and only if they have not been pre-set. This allows them to be
    created outside the event loop, and gives more predictable behavior and
    some performance gains.
  + They now prevent concurrent calls to the wait method by raising a
    `RuntimeError` in such situations, making them safer. Previously, this was
    not handled in any way on the `aiologic` side, which required special care
    and could lead to undefined behavior if the conditions for their use were
    not met.
  + Placeholder events now inherit `aiologic.lowlevel.GreenEvent` and
    `aiologic.lowlevel.AsyncEvent`, allowing them to be used in code sections
    where wait methods are called.
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
- Events have been rewritten:
  + They no longer save their state when being pickled/copied. So they now
    share the same behavior as the other synchronization primitives.
  + The `value` parameter of `aiologic.CountdownEvent` has been renamed to
    `initial_value`. Accordingly, a property with the same name has also been
    added.
- Barriers have been rewritten:
  + The `parties` parameter now has a default value of `0`. This allows
    barriers to be used directly as default factories.
  + They now allow passing `parties` equal to `0`, with which they ignore the
    waiting queue length (they only wake up tasks when `abort()` is called
    directly or indirectly, e.g. on cancellation or timeout).
  + Single-use barriers can now be used correctly in a Boolean context: `True`
    if the current state is not filling, `False` otherwise.
  + They now do not prevent concurrent `abort()` calls from affecting
    successful task wakeup. This change is due to the fact that they cannot
    suppress cancellation in principle, making the prevention of
    `BrokenBarrierError` on successful wakeup meaningless. As a consequence,
    single-use barriers can now be broken after use (e.g. via an `abort()`
    call).
- Semaphores have been rewritten:
  + `aiologic.Semaphore` now disallow passing `max_size` other than `None` from
    subclasses. Previously it was ignored, which could violate user
    expectations intending to get `aiologic.BoundedSemaphore` behavior.
  + `aiologic.BoundedSemaphore` (and consequently `aiologic.Semaphore`) now
    creates `aiologic.BoundedBinarySemaphore` when `max_size` <= 1. This makes
    it possible to use an implementation that is more efficient in both time
    and memory without importing new classes.
  + `aiologic.BoundedSemaphore.release()` now disallows `count=0`. Previously,
    it allowed threads to participate in waking up others during race
    conditions, but `aiologic.Semaphore.release()` no longer has such
    semantics.
- Capacity limiters have been rewritten:
  + `CapacityLimiter.borrowers` is now a read-only property that returns a
    read-only mapping proxy, which increases safety when working with it.
  + The `total_tokens` parameter now has a default value of `1`. This allows
    capacity limiters to be used directly as default factories and makes their
    interface a bit closer to semaphores.
  + They can now be used correctly in a Boolean context: `True` if at least one
    token has been borrowed, `False` otherwise.
- Locks have been rewritten:
  + They now set `owner` (and `count`) on release rather than on wakeup. This
    gives the expected values of these parameters when locks are used
    cooperatively. Previously, it was not possible to determine the next lock
    owner after release in the same task (it was `None`).
- Condition variables have been rewritten:
  + They now only support passing low-level (thread-level) locks (synchronous
    mode), binary semaphores and high-level locks (mixed mode), and `None`
    (lockless mode). This change was made to simplify their implementation. For
    special cases it is recommended to use low-level events directly.
  + Waiting for a predicate now supports delegating its checking to notifiers
    and is the default (`delegate=True`). This reduces the number of context
    switches to the minimum necessary.
  + For high-level primitives, all waits are now truly fair and always run with
    exactly one checkpoint (exactly two in case of cancel), just like all other
    `aiologic` functions. This works by using a new reparking mechanism and
    solves the well-known [resource starvation
    issue](https://github.com/python/cpython/issues/90968).
  + They now count the number of lock acquires to avoid redundant `release()`
    calls when used as context managers. Because of this, they will now never
    throw a `RuntimeError` when a `wait()` call fails (e.g. due to a
    `KeyboardInterrupt` while trying to reacquire
    `aiologic.lowlevel.ThreadLock`) except in the case of concurrent `notify()`
    calls. This makes it safe (with some caveats) to use condition variables
    even when shielding from external cancellation is not guaranteed.
  + They now shield lock state restoring not only in async methods, but also in
    green methods. It is still not guaranteed that a `wait()` call cannot be
    cancelled in any unpredictable way (e.g. when a greenlet is killed by an
    exception other than `GreenletExit`), but now condition variables can be
    safely used in more scenarios.
  + They now check that the current task is the owner of the lock before
    starting the wait. This corresponds to the behavior of the standard
    condition variables, and allows exceptions to be raised with more
    meaningful messages.
  + They now check that the current task is the owner of the lock before
    starting notification for predicates for all variations, and in general for
    any calls for high-level primitives. While this change reduces the number
    of scenarios in which condition variables can be used, it provides the
    thread-safety needed for the new features to work.
  + They now always yield themselves when used as context managers. This
    diverges from the standard condition variables, but makes the interface
    more consistent.
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
- Resource guards have been rewritten:
  + They are now interpreted in a Boolean context in the same way as locks.
    Previously, they returned opposite values.
- Queues have been rewritten:
  + They no longer support the `_qsize()` (returns queue size) and `_items()`
    (returns a list of queue items) overrides, and they have been removed
    accordingly. Unlike the other overridden methods, they required
    thread-safety on the user side, which could cause additional difficulties.
    It is now recommended to use queues from
    [culsans](https://github.com/x42005e1f/culsans), a derivative of
    `aiologic`, to create full-featured custom queues.
- The representation of primitives has been changed. All instances now include
  the module name, use the correct class name in subclasses (except for
  private classes) and show their status in representation.
- `aiologic.lowlevel.current_green_token()` now returns the current thread, and
  `aiologic.lowlevel.current_green_token_ident()` now uses the current thread
  ID for `threading`. This makes these functions more meaningful, and leads to
  the expected behavior in group-level locks. Previously, constant values were
  returned for `threading`.
- `aiologic.lowlevel.current_green_token()` and
  `aiologic.lowlevel.current_green_task()` now return main greenlet objects for
  `gevent`'s pool of native worker threads (and for any dummy threads when
  `greenlet` is imported). This allows these functions to be used with `gevent`
  without additional handlers.
- The first `aiologic.lowlevel.current_thread()` call no longer patches the
  `threading` module for PyPy (to fix the race in `Thread.join()`). This is
  done to eliminate side effects and possible conflicts with debuggers. Use
  PyPy 7.3.18 or higher instead, or apply [a separate
  patch](https://gist.github.com/x42005e1f/e50cc904867f2458a546c9e2f51128fe)
  yourself.
- The first `aiologic.lowlevel.GreenEvent` instantiation no longer injects
  `destroy()` into `eventlet` hubs. This is delegated to [a separate
  patch](https://gist.github.com/x42005e1f/e50cc904867f2458a546c9e2f51128fe) as
  it gives more predictable behavior. However, `aiologic` still injects
  `schedule_call_threadsafe()` since
  [eventlet/eventlet#1023](https://github.com/eventlet/eventlet/issues/1023) is
  still unresolved.
- `curio` events now use lockless futures instead of
  `concurrent.futures.Future`. This makes the implementation of `curio` support
  completely non-blocking (like the rest of the concurrency libraries), which
  has a positive impact on performance.
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

- `timeout<0` in all primitives, as they differ from the semantics of the
  standard library, which could lead to their incorrect use (since they are
  equivalent `timeout=0`, but not to no timeout).
- `action` as a positional parameter in `aiologic.ResourceGuard` in favor of
  using it as a keyword-only parameter.
- `maxsize<=0` in complex queue constructors in favor of `maxsize=None`:
  support for `maxsize<0` is not pythonic, goes against common style, and
  `maxsize=0` may in the future be used to create special empty queues.
- `aiologic.PLock` in favor of `aiologic.BinarySemaphore`.
- `aiologic.RLock.level` in favor of `aiologic.RLock.count`.
- `aiologic.lowlevel.MISSING` in favor of `aiologic.meta.MISSING`.
- `aiologic.lowlevel.GreenEvent` and `aiologic.lowlevel.AsyncEvent` direct
  creation in favor of `aiologic.lowlevel.create_green_event()` and
  `aiologic.lowlevel.create_async_event()`: they will become protocols in the
  future.
- `aiologic.lowlevel.Flag` in favor of `aiologic.Flag`.
- `aiologic.lowlevel.checkpoint()` in favor of
  `aiologic.lowlevel.async_checkpoint()` (previously alias): checkpoints are
  now strictly separated into green and async checkpoints.

### Removed

- `aiologic.CapacityLimiter.*_on_behalf_of()` methods: they did not provide the
  proper thread-safety level (capacity limiters need to be higher-level
  primitives for this), but also made the implementation more complex and thus
  degraded performance.
- `is_set` parameter from one-time and reusable events (`aiologic.Event` and
  `aiologic.REvent`).
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

- Slotted classes lacked `__getstate__()`, which caused internal fields to be
  copied during pickling even if `__getnewargs__()` was defined. As a result,
  it was impossible to copy primitives while using them.
- In `aiologic.lowlevel.shield()` (previously
  `aiologic.lowlevel.repeat_if_cancelled()`):
  + Hangs could occur when using `anyio.CancelScope()` with the `asyncio`
    backend. Now this case is handled in a special way. Related:
    [agronholm/anyio#884](https://github.com/agronholm/anyio/issues/884).
  + Reference cycles were possible when another exception was raised after a
    `asyncio.CancelledError` was caught: in this case, the last
    `asyncio.CancelledError` was not removed from the frame.
- `aiologic.lowlevel.current_thread()` returned:
  + another main thread object after monkey patching the `threading` module
    with `eventlet` (now the same as from `threading.main_thread()`).
  + `None` for the main thread after monkey patching the `threading` module
    with `gevent` (now the same as from `threading.main_thread()`).
  + green thread objects for dummy threads whose identifier matched the running
    greenlets (now raises an exception according to the new behavior).
- The initialization of low-level waiter classes was protected from concurrent
  execution using a mutex, which could lead to deadlock if it was interrupted
  and retried in the same thread. Now, `aiologic.lowlevel.ThreadOnceLock` is
  used for this (via `aiologic.lowlevel.once()`), which ensures signal-safety.
- Using `aiologic.RLock` from inside a signal handler or destructor could
  result in a false release if the execution occurred inside an `*_acquire()`
  call after setting the `owner` property but before setting the `count`
  property. The order of operations is now inverted. This makes
  `aiologic.RLock` a bit more signal-safe than `threading._PyRLock`.
- Using checkpoints for `threading` could cause hub spawning in worker threads
  when `aiologic` is imported after monkey patching the `time` module with
  `eventlet` or `gevent`. As a result, the open files limit could have been
  exceeded.
- Blocking `eventlet` calls did not check the context, which could lead to
  incorrect behavior when executing blocking calls in the hub context (as part
  of scheduled calls).
- The locks and semaphores (and the capacity limiters and simple queues based
  on them) did not handle exceptions at checkpoints, so that cancelling at
  checkpoints (`trio` case by default) did not release the primitive.
- The methods of complex queues (all except `aiologic.SimpleQueue`) used an
  incorrect condition for cancellation handling, which could break
  thread-safety after cancellation. Now the handling is changed to match that
  of locks and semaphores, which additionally speeds up methods by reducing
  operations.
- Complex queues did not remove the event from the secondary internal queue on
  unsuccessful cancellation, which could lead to memory leaks in some
  situations.
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
  through repeatedly.
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

[0.16.0]: https://github.com/x42005e1f/aiologic/compare/0.15.0...0.16.0
[0.15.0]: https://github.com/x42005e1f/aiologic/compare/0.14.0...0.15.0
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
