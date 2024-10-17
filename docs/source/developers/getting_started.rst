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

.. tip::
  This project includes a :link:`devcontainer` which can be used for development.
  It provides all of the tools required (node, :link:`npm`, :link:`poetry`, :link:`python`, etc) for development and a few bonuses for *quality of life* (:link:`direnv`, :lin:`vscode` extensions, etc).

  .. seealso::
    - `Devcontainers: Personalizing with dotfile repositories <https://code.visualstudio.com/docs/devcontainers/containers#_personalizing-with-dotfile-repositories>`__
    - `Personalizing GitHub Codespaces for your account <https://docs.github.com/en/codespaces/setting-your-user-preferences/personalizing-github-codespaces-for-your-account>`__


  It's not required to use this for development work, but does provide an easy and consistent way to get started.

This project uses :link:`poetry` to create Python virtual environment.
This must be installed on your system before setting up your dev environment.
Additionally, the :link:`poetry-dynamic-versioning` plugin should be installed.
Refer to the documentation of :link:`poetry-dynamic-versioning` for how to install it based on how you installed :link:`poetry`.

With :link:`poetry` installed, run ``make setup`` to setup your development environment.
This will create all the required virtual environments to work on Runway, build docs locally, and run integration tests locally.
The virtual environments all have Runway installed as editable meaning as you make changes to the code of your local clone, it will be reflected in all the virtual environments.

pre-commit
==========

:link:`pre-commit` is configured for this project to help developers follow the coding style.
If you used ``make setup`` to setup your environment, it is already setup for you.
If not, you can run ``make setup-pre-commit`` to to install the pre-commit hooks.

You can also run ``make run-pre-commit`` at any time to manually trigger these hooks.


pyright Type Checking
=====================

This project uses :link:`pyright` to perform type checking. To run type checking locally, install pyright (``make setup-npm``) then run ``make lint`` or ``make lint-pyright``.
