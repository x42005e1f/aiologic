#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

__all__ = ()

import sys

from .patcher import import_original

error = OSError

if sys.version_info >= (3, 10):
    timeout = TimeoutError

# third-party patchers can break the original objects from the socket module,
# so we need to use the _socket module in the first place

try:
    try:
        socket = import_original("_socket:socket")
    except ImportError:
        socket = import_original("socket:socket")

    try:
        socketpair = import_original("_socket:socketpair")
    except ImportError:
        try:
            AF_INET = import_original("_socket:AF_INET")
        except ImportError:
            AF_INET = import_original("socket:AF_INET")

        try:
            AF_INET6 = import_original("_socket:AF_INET6")
        except ImportError:
            AF_INET6 = import_original("socket:AF_INET6")

        try:
            SOCK_STREAM = import_original("_socket:SOCK_STREAM")
        except ImportError:
            SOCK_STREAM = import_original("socket:SOCK_STREAM")

        # see socket._fallback_socketpair()
        def socketpair(family=AF_INET, type=SOCK_STREAM, proto=0):
            if family == AF_INET:
                host = "127.0.0.1"
            elif family == AF_INET6:
                host = "::1"
            else:
                raise ValueError(
                    "Only AF_INET and AF_INET6 socket address families"
                    " are supported"
                )

            if type != SOCK_STREAM:
                raise ValueError("Only SOCK_STREAM socket type is supported")

            if proto != 0:
                raise ValueError("Only protocol zero is supported")

            lsock = socket(family, type, proto, None)

            try:
                lsock.bind((host, 0))
                lsock.listen()

                addr, port = lsock.getsockname()[:2]
                csock = socket(family, type, proto, None)

                try:
                    csock.setblocking(False)

                    try:
                        csock.connect((addr, port))
                    except (BlockingIOError, InterruptedError):
                        pass

                    csock.setblocking(True)

                    if hasattr(lsock, "accept"):
                        ssock, _ = lsock.accept()
                    else:
                        fd, _ = lsock._accept()
                        ssock = socket(family, type, proto, fd)
                except:
                    csock.close()
                    raise
            finally:
                lsock.close()

            try:
                if (
                    ssock.getsockname() != csock.getpeername()
                    or csock.getsockname() != ssock.getpeername()
                ):
                    raise ConnectionError("Unexpected peer connection")
            except:
                ssock.close()
                csock.close()

                raise

            return (ssock, csock)

except ImportError:
    pass


def __getattr__(name, /):
    if not name.startswith("__") or not name.endswith("__"):
        for template in ("_socket:{}", "socket:{}"):
            try:
                value = import_original(template.format(name))
            except ImportError:
                pass
            else:
                if name.isupper() or getattr(value, "__module__", "") == (
                    "_socket"
                ):
                    return globals().setdefault(name, value)

    raise AttributeError(f"module '_socket' has no attribute {name!r}")
