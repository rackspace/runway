#####################################
Building Pyinstaller Packages Locally
#####################################

We use Pyinstaller_ to build executables that do not require Python to be installed on a system.
These are built by Travis CI for distribution to ensure a consistent environment but they can also be build locally for testing.

.. _Pyinstaller: https://pypi.org/project/PyInstaller/


*************
Prerequisites
*************

These need to be installed globally.

- `poetry <https://python-poetry.org/>`__


*******
Process
*******

1. Export ``OS_NAME`` environment variable for your system (``ubuntu-20.04``, ``macos-12``, or ``windows-latest``).
2. Execute ``make build-pyinstaller-file`` or ``make build-pyinstaller-folder`` from the root of the repo.

The output of these commands can be found in ``./artifacts``
