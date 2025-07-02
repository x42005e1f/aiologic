#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

from ._executors import (
    TaskExecutor as TaskExecutor,
    create_executor as create_executor,
    current_executor as current_executor,
    run as run,
)
