#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from _socket import socket

def socketpair(
    family: int = ...,
    type: int = ...,
    proto: int = 0,
    *,
    blocking: bool = True,
    buffering: int = -1,
) -> tuple[socket, socket]: ...
