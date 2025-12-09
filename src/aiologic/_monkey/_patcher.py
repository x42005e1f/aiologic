#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from __future__ import annotations

from wrapt import patch_function_wrapper


def patch_eventlet() -> None:
    # Injects `schedule_call_threadsafe()` (a thread-safe variant of
    # `schedule_call_global()`) into eventlet hubs to schedule calls from other
    # threads.

    # >>> from threading import Timer
    # >>> from eventlet.event import Event
    # >>> from eventlet.hubs import get_hub
    # >>> patch_eventlet()
    # >>> event = Event()
    # >>> Timer(1, get_hub().schedule_call_threadsafe, [0, event.send]).start()
    # >>> event.wait()  # will take 1 second

    # Also supports `destroy()` injected by a separate patch
    # (https://gist.github.com/x42005e1f/e50cc904867f2458a546c9e2f51128fe).

    from eventlet.hubs.asyncio import Hub as AsyncioHub
    from eventlet.hubs.hub import BaseHub
    from eventlet.hubs.timer import Timer
    from eventlet.patcher import original

    if hasattr(BaseHub, "schedule_call_threadsafe"):
        return

    if hasattr(BaseHub, "destroy"):

        @patch_function_wrapper("eventlet.hubs.hub", "BaseHub.destroy")
        def BaseHub_destroy_wrapper(wrapped, instance, args, kwargs, /):
            try:
                rsock = instance._threadsafe_rsock
            except AttributeError:
                pass
            else:
                rsock.close()

            try:
                wsock = instance._threadsafe_wsock
            except AttributeError:
                pass
            else:
                wsock.close()

            return wrapped(*args, **kwargs)

    socket = original("socket")

    def BaseHub__init_socketpair(self, /):
        if not hasattr(self, "_threadsafe_wsock"):
            rsock, wsock = socket.socketpair()
            rsock_fd = rsock.fileno()

            rsock.setblocking(False)
            wsock.setblocking(False)

            rsock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1)
            wsock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1)

            try:
                wsock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            except OSError:
                pass

            def rsock_recv(_):
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

            self._threadsafe_rsock = rsock
            self._threadsafe_wsock = wsock

    BaseHub._init_socketpair = BaseHub__init_socketpair

    def AsyncioHub__init_socketpair(self, /):
        pass

    AsyncioHub._init_socketpair = AsyncioHub__init_socketpair

    @patch_function_wrapper("eventlet.hubs.hub", "BaseHub.prepare_timers")
    def BaseHub_prepare_timers_wrapper(wrapped, instance, args, kwargs, /):
        instance._init_socketpair()

        try:
            timers = instance._threadsafe_timers
        except AttributeError:
            pass
        else:
            if timers:
                items = timers.copy()

                instance.next_timers.extend(items)

                del timers[: len(items)]

        return wrapped(*args, **kwargs)

    def BaseHub__threadsafe_wakeup(self, /):
        try:
            wsock = self._threadsafe_wsock
        except AttributeError:
            pass
        else:
            try:
                wsock.send(b"\x00")
            except OSError:
                pass

    BaseHub._threadsafe_wakeup = BaseHub__threadsafe_wakeup

    def AsyncioHub__threadsafe_wakeup(self, /):
        try:
            self.loop.call_soon_threadsafe(self.sleep_event.set)
        except RuntimeError:  # event loop is closed
            pass

    AsyncioHub._threadsafe_wakeup = AsyncioHub__threadsafe_wakeup

    def BaseHub_schedule_call_threadsafe(
        self,
        seconds,
        callback,
        /,
        *args,
        **kwargs,
    ):
        timer = Timer(seconds, callback, *args, **kwargs)
        scheduled_time = self.clock() + seconds

        try:
            timers = self._threadsafe_timers
        except AttributeError:
            timers = vars(self).setdefault("_threadsafe_timers", [])

        timers.append((scheduled_time, timer))
        self._threadsafe_wakeup()

        # timer methods are not thread-safe, so we do not return it

    BaseHub.schedule_call_threadsafe = BaseHub_schedule_call_threadsafe
