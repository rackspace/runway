#####################################
Building Pyinstaller Packages Locally
#####################################

We use Pyinstaller_ to build executables that do not require Python to be installed on a system.
These are built by Travis CI for distribution to ensure a consistent environment but they can also be build locally for testing.

.. _Pyinstaller: https://pypi.org/project/PyInstaller/


*************
Prerequisites
*************

These need to be installed globally so they are not included in the Pipfile.

- ``setuptools==45.2.0``
- ``virtualenv==16.7.9``
- ``pipenv==2018.11.26``


*******
Process
*******

1. Export ``OS_NAME`` environment variable for your system (``ubuntu-latest``, ``macos-latest``, or ``windows-latest``).
2. Execute ``make build_pyinstaller_file`` or ``make build_pyinstaller_folder`` from the root of the repo.

The output of these commands can be found in ``./artifacts``
