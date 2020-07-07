.. _python-setup:

Python Setup
============

Perform the following to install/configure Python & package management tools.

.. note:: All commands below are to be run as your user.
          (i.e. not root/sudo/Administrator).

1. Ensure you have a working python environment:
    - On macOS:
        - Note: Substitute ``.bash_profile`` in place of ``.zshrc`` below if using Bash (e.g. macOS pre-Catalina)
        - Add local python bin directories to $PATH::

            PYTHONVER=$(python3 -c "import sys;print(str(sys.version_info.major)+'.'+str(sys.version_info.minor))")
            if ! grep -s '\.local\/bin' ~/.zshrc > /dev/null 2>&1 || ! grep -s "Library\/Python\/$PYTHONVER/bin" ~/.zshrc > /dev/null 2>&1 ; then echo "export PATH=\"\$HOME/Library/Python/$PYTHONVER/bin:\$HOME/.local/bin:\$PATH\"" >> ~/.zshrc; fi

        - Run ``source ~/.zshrc`` to use the updated PATH.

    - On Windows:
        - Install `Python <https://www.python.org/>`_ (choose the latest ``Windows x86-64 executable installer`` and run it):
            - On the initial setup page, click ``Customize installation``
            - Leave all Optional Features selected, and click Next
            - On the Advanced Options page change the following options and click Install:
                - Check the ``Install for all users`` and ``Add Python to environment variables`` options.
                - Change the install location to ``C:\Python37`` (updating ``Python37`` to the appropriate directory for the installed version, e.g. ``Python38`` for Python 3.8)
            - At the ``Setup was successful`` screen, click ``Disable path length limit`` and then close the setup program.
        - Edit the Path environment variable for your user:
            - In the Start Menu, start typing ``environment variables`` and select ``Edit environment variables for your account``.
            - In the User variables for your username, select ``Path`` and click ``Edit...``
            - Append ``%USERPROFILE%\AppData\Roaming\Python\Python37\Scripts`` & ``%USERPROFILE%\.local\bin`` to the current Variable values and click Ok
                - Change ``Python37`` to the appropriate directory for the installed version (e.g. ``Python38`` for Python 3.8)
                - In Windows Server 2016, the value is shown in a single line -- add it with semicolons::

                    %USERPROFILE%\AppData\Roaming\Python\Python37\Scripts;%USERPROFILE%\.local\bin;

            - Click Ok to close the Environment Variables window.
            - Close all existing PowerShell windows and launch a new one to use the updated PATH.

    - On Ubuntu Linux:
        - Add local python bin directory to $PATH::

            if ! grep 'HOME\/\.local\/bin' ~/.bash_profile > /dev/null 2>&1; then echo 'export PATH=$HOME/.local/bin:$PATH' >> ~/.bash_profile; fi

        - Run ``source ~/.bash_profile`` to use the updated PATH.
        - Install Python 3 and dependencies::

            sudo apt -y install python3-pip

2. Install python package managers::

        pip3 install --user pipenv pipx

Package Installation
--------------------

Afterwards, your user will be able to install additional Python packages using
one of the following tools. Each wraps the base pip package manager and
automatically manages virtual environments to ensure package dependencies don't
conflict.

pipx
~~~~

Global CLIs & utilities, like the AWS CLI, can be installed via
`pipx <https://github.com/pipxproject/pipx>`_::

        pipx install awscli

pipenv
~~~~~~

Utilities used in a project should generally have their versions stored in the
project repository, so users (now and in the future) and remote build systems
use the same versions specified in the repo.

`pipenv <https://github.com/pipxproject/pipx>`_ works similarly to pipx, but
creates a lockfile that can be checked into a repo::

        pipenv install runway
