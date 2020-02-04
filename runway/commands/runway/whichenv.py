"""Identify the current environment and print it to the terminal.

When run, the environment is determined from the current git branch
unless ``ignore_git_branch: true`` is specified in the
:ref:`Runway config file<runway-config>`. If the ``DEPLOY_ENVIRONMENT``
environment variable is set, it's value will be used. If neither the git
branch or environment variable are available, the directory name is used.
The environment identified here is used to determine the env/config files
to use. It is also used with options defined in the Runway config file
such as ``assume_role``, ``account_id``, etc. See
:ref:`Runway Config<runway-config>` for details on these options.

Example:
  .. code-block:: shell

    $ runway whichenv
    common

"""
from __future__ import print_function
import logging

from ..runway_command import RunwayCommand, get_env


class WhichEnv(RunwayCommand):
    """Extend RunwayCommand with execute to run the get_env method."""

    def execute(self):
        """Output environment name."""
        logging.getLogger('runway').setLevel(logging.ERROR)  # suppress warnings
        print(get_env(
            self.env_root,
            self.runway_config.ignore_git_branch
        ))
