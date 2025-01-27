#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: CC0-1.0

from importlib.metadata import version as get_version

from packaging.version import parse as parse_version

project = "aiologic"
author = "Ilya Egorov"
copyright = "2025 Ilya Egorov"

v = parse_version(get_version("aiologic"))
version = v.base_version
release = v.public

extensions = [
    "sphinx_rtd_theme",
    "myst_parser",
]

html_theme = "sphinx_rtd_theme"
html_theme_options = {}
