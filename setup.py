#!/usr/bin/env python3

import os

from setuptools import find_namespace_packages, setup

if __name__ == '__main__':
    setup(
        package_dir={'': 'src'},
        packages=find_namespace_packages(where='src'),
        py_modules=[
            entry.name[:-3]
            for entry in os.scandir('src')
            if (
                not entry.name.startswith('.')
                and entry.name.endswith('.py')
                and entry.is_file()
            )
        ]
    )
