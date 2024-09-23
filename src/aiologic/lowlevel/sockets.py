#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

__all__ = ("socketpair",)

try:
    from .socket import socketpair as socketpair_impl
except ImportError:

    def socketpair(*args, blocking=True, buffering=-1, **kwargs):
        raise NotImplementedError

else:
    try:
        from .socket import SOL_SOCKET, SO_RCVBUF, SO_SNDBUF
    except ImportError:
        pass

    try:
        from .socket import IPPROTO_TCP, TCP_NODELAY
    except ImportError:
        pass

    def socketpair(*args, blocking=True, buffering=-1, **kwargs):
        r, w = socketpair_impl(*args, **kwargs)

        if not blocking:
            r.setblocking(False)
            w.setblocking(False)

        if buffering >= 0:
            try:
                r.setsockopt(SOL_SOCKET, SO_RCVBUF, buffering)
                w.setsockopt(SOL_SOCKET, SO_SNDBUF, buffering)
            except (NameError, OSError):
                pass

        try:
            w.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
        except (NameError, OSError):
            pass

        return (r, w)
