#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: ISC

"""
This package implements some metaprogramming techniques and concepts that are
used for the library's own needs. Although many of them are designed for
internal use, you can also use them for your own purposes.
"""

from ._exports import (
    export as export,
    export_deprecated as export_deprecated,
    export_dynamic as export_dynamic,
)
from ._functions import (
    copies as copies,
    replaces as replaces,
)
from ._helpers import (
    await_for as await_for,
)
from ._imports import (
    import_from as import_from,
    import_module as import_module,
)
from ._markers import (
    DEFAULT as DEFAULT,
    MISSING as MISSING,
    DefaultType as DefaultType,
    MissingType as MissingType,
    SingletonEnum as SingletonEnum,
)
from ._modules import (
    resolve_name as resolve_name,
)
