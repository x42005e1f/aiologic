..
  SPDX-FileCopyrightText: 2025 Ilya Egorov <0x42005e1f@gmail.com>
  SPDX-License-Identifier: CC-BY-4.0

Installation
============

.. include:: ../README.rst
  :start-after: .. installation-start-marker
  :end-before: .. installation-end-marker

Third-party distributions
-------------------------

Various third-parties provide aiologic for their environments.

Anaconda.org
^^^^^^^^^^^^

aiologic is available via the `conda-forge community channel <https://
anaconda.org/conda-forge/aiologic>`__:

.. code:: console

    conda install conda-forge::aiologic

You can also use the `mamba <https://github.com/mamba-org/mamba>`__ package
manager instead of conda.

piwheels
^^^^^^^^

aiologic is also available via the `piwheels <https://www.piwheels.org/project/
aiologic/>`__, a Python package repository which provides pre-compiled packages
for the Raspberry Pi. Installation is similar to that from PyPI, but you will
need to change your pip configuration or explicitly specify the required index
according to the `FAQ <https://www.piwheels.org/faq.html>`__.
