#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
# SPDX-License-Identifier: CC0-1.0

import os
import sys

from importlib.metadata import version as get_version

from packaging.version import parse as parse_version

os.environ["SPHINX_AUTODOC_RELOAD_MODULES"] = "1"

project = "aiologic"
author = "Ilya Egorov"
copyright = "2025 Ilya Egorov"

v = parse_version(get_version("aiologic"))
version = v.base_version
release = v.public

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx_copybutton",
    "sphinx_inline_tabs",
    "sphinx_rtd_theme",
]

if sys.version_info >= (3, 11):
    extensions.append("sphinxcontrib.autodoc_inherit_overload")

autodoc_class_signature = "separated"
autodoc_inherit_docstrings = False
autodoc_default_options = {
    "member-order": "bysource",
    "show-inheritance": True,
}

intersphinx_mapping = {
    "aiohttp": ("https://docs.aiohttp.org/en/stable/", None),
    "eventlet": ("https://eventlet.readthedocs.io/en/stable/", None),
    "python": ("https://docs.python.org/3", None),
    "twisted": ("https://docs.twisted.org/en/stable/api/", None),
}

html_theme = "sphinx_rtd_theme"
html_theme_options = {}
html_static_path = ["_static"]
html_css_files = ["css/custom.css"]
html_context = {
    "display_github": True,
    "github_user": "x42005e1f",
    "github_repo": "aiologic",
    "github_version": "main",
    "conf_py_path": "/docs/",
}
