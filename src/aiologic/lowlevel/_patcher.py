#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from functools import wraps

from ._threads import once


@once
def patch_eventlet():
    """
    Injects `destroy()` into `BaseHub` to fix EMFILE ("too many open files")
    + ENOMEM (memory leak).

    Code to reproduce::

        from threading import Thread

        import eventlet
        import eventlet.hubs

        stop = False

        def func():
            global stop

            try:
                eventlet.sleep()
            except:
                stop = True
                raise
            finally:
                hub = eventlet.hubs.get_hub()

                try:
                    destroy = hub.destroy
                except AttributeError:
                    pass
                else:
                    destroy()

        while not stop:
            thread = Thread(target=func)
            thread.start()
            thread.join()

    Also injects `schedule_call_threadsafe()` (a thread-safe variant of
    `schedule_call_global()`).
    """

    def inject_destroy(BaseHub):
        if hasattr(BaseHub, "destroy"):
            return  # what was applied?!

        def BaseHub_destroy(self, /):
            if not self.greenlet.dead:
                self.abort(wait=True)

        BaseHub.destroy = BaseHub_destroy

        try:
            from eventlet.hubs.epolls import Hub as EpollHub
        except ImportError:
            pass
        else:

            def EpollHub_destroy(self, /):
                super(self.__class__, self).destroy()
                self.poll.close()

            EpollHub.destroy = EpollHub_destroy

        try:
            from eventlet.hubs.kqueue import Hub as KqueueHub
        except ImportError:
            pass
        else:

            def KqueueHub_destroy(self, /):
                super(self.__class__, self).destroy()
                self.kqueue.close()

            KqueueHub.destroy = KqueueHub_destroy

        try:
            from eventlet.hubs.asyncio import Hub as AsyncioHub
        except ImportError:
            pass
        else:

            def AsyncioHub_destroy(self, /):
                super(self.__class__, self).destroy()
                self.loop.close()

            AsyncioHub.destroy = AsyncioHub_destroy

    def inject_schedule_call_threadsafe(BaseHub):
        if hasattr(BaseHub, "schedule_call_threadsafe"):
            return  # what was applied?!

        from eventlet.hubs.timer import Timer

        from . import _monkey

        socket = _monkey._import_eventlet_original("socket")

        def BaseHub_schedule_call_threadsafe(self, /, *args, **kwargs):
            timer = Timer(*args, **kwargs)
            scheduled_time = self.clock() + timer.seconds

            try:
                timers = self._aiologic_threadsafe_timers
            except AttributeError:
                timers = vars(self).setdefault(
                    "_aiologic_threadsafe_timers",
                    [],
                )

            timers.append((scheduled_time, timer))

            try:
                wsock = self._aiologic_wsock
            except AttributeError:
                pass
            else:
                try:
                    wsock.send(b"\x00")
                except OSError:
                    pass

            # timer methods are not thread-safe, so we don't return it

        BaseHub.schedule_call_threadsafe = BaseHub_schedule_call_threadsafe

        try:
            from eventlet.hubs.asyncio import Hub as AsyncioHub
        except ImportError:
            pass
        else:

            def AsyncioHub_schedule_call_threadsafe(self, /, *args, **kwargs):
                timer = Timer(*args, **kwargs)
                scheduled_time = self.clock() + timer.seconds

                try:
                    timers = self._aiologic_threadsafe_timers
                except AttributeError:
                    timers = vars(self).setdefault(
                        "_aiologic_threadsafe_timers",
                        [],
                    )

                timers.append((scheduled_time, timer))

                try:
                    self.loop.call_soon_threadsafe(self.sleep_event.set)
                except RuntimeError:  # event loop is closed
                    pass

                # timer methods are not thread-safe, so we don't return it

            AsyncioHub.schedule_call_threadsafe = (
                AsyncioHub_schedule_call_threadsafe
            )

        def BaseHub__aiologic_init_socketpair(self, /):
            if not hasattr(self, "_aiologic_rsock"):
                rsock, wsock = socket.socketpair()
                rsock_fd = rsock.fileno()

                rsock.setblocking(False)
                wsock.setblocking(False)

                try:
                    rsock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1)
                    wsock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1)
                except (AttributeError, OSError):
                    pass

                try:
                    wsock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                except (AttributeError, OSError):
                    pass

                def rsock_recv(_, /):
                    while True:
                        try:
                            data = rsock.recv(4096)
                        except InterruptedError:
                            continue
                        except BlockingIOError:
                            break
                        else:
                            if not data:
                                break

                def rsock_throw(exc, /):
                    raise exc

                self.mark_as_reopened(rsock_fd)
                self.add(self.READ, rsock_fd, rsock_recv, rsock_throw, None)

                self._aiologic_rsock = rsock
                self._aiologic_wsock = wsock

        BaseHub._aiologic_init_socketpair = BaseHub__aiologic_init_socketpair

        try:
            from eventlet.hubs.asyncio import Hub as AsyncioHub
        except ImportError:
            pass
        else:

            def AsyncioHub__aiologic_init_socketpair(self, /):
                pass

            AsyncioHub._aiologic_init_socketpair = (
                AsyncioHub__aiologic_init_socketpair
            )

        BaseHub_prepare_timers_impl = BaseHub.prepare_timers

        @wraps(BaseHub.prepare_timers)
        def BaseHub_prepare_timers(self, /):
            self._aiologic_init_socketpair()

            try:
                timers = self._aiologic_threadsafe_timers
            except AttributeError:
                pass
            else:
                while timers:
                    items = timers.copy()

                    self.next_timers.extend(items)

                    del timers[: len(items)]

            BaseHub_prepare_timers_impl(self)

        BaseHub.prepare_timers = BaseHub_prepare_timers

        BaseHub_destroy_impl = BaseHub.destroy

        @wraps(BaseHub.destroy)
        def BaseHub_destroy(self, /):
            BaseHub_destroy_impl(self)

            try:
                rsock = self._aiologic_rsock
            except AttributeError:
                pass
            else:
                rsock.close()

            try:
                wsock = self._aiologic_wsock
            except AttributeError:
                pass
            else:
                wsock.close()

        BaseHub.destroy = BaseHub_destroy

    from eventlet.hubs.hub import BaseHub

    inject_destroy(BaseHub)
    inject_schedule_call_threadsafe(BaseHub)
