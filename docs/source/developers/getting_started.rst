.. _dev-getting-started:

###############
Getting Started
###############

Before getting started, `fork this repo`_ and `clone your fork`_.

.. _fork this repo: https://help.github.com/en/github/getting-started-with-github/fork-a-repo
.. _clone your fork: https://help.github.com/en/github/creating-cloning-and-archiving-repositories/cloning-a-repository


***********************
Development Environment
***********************

This project includes an optional `VSCode Dev Container <https://code.visualstudio.com/docs/remote/containers>`__. This is an Ubuntu 22.04 image that will launch with operating system pre-requisites already installed and VSCode configured for Python debugging. It's not required to use this for development work, but does provide an easy and consistent way to get started.

This project uses `poetry <https://python-poetry.org/>`__ to create Python virtual environment. This must be installed on your system before setting up your dev environment.

With poetry installed, run ``make setup`` to setup your development environment.
This will create all the required virtual environments to work on Runway, build docs locally, and run integration tests locally.
The virtual environments all have Runway installed as editable meaning as you make changes to the code of your local clone, it will be reflected in all the virtual environments.


pre-commit
==========

`pre-commit <https://pre-commit.com/>`__ is configured for this project to help developers follow the coding style.
If you used ``make setup`` to setup your environment, it is already setup for you.
If not, you can run ``make setup-pre-commit`` to to install the pre-commit hooks.

You can also run ``make run-pre-commit`` at any time to manually trigger these hooks.


pyright Type Checking
=====================

This project uses pyright to perform type checking. To run type checking locally, install pyright (``make npm-ci``) then run ``make lint`` or ``make lint-pyright``.
