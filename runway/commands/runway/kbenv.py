"""Manage versions and execute `Kubernetes`_ commands.

Runway's built-in kubectl version management ensure the correct version
is used for a given environment. Define a ``.kubectl-version`` file
in your k8s module and that version will be automatically downloaded &
used during Runway operations.

The ``tfenv`` subcommand supplements this functionality in 2 ways:

* The ``install`` option will download kubectl (e.g. for
  pre-seeding a deployment system)
* The ``run`` option will execute arbitrary kubectl commands

Examples:
  .. code-block:: shell

    $ runway kbenv install 1.14.5
    $ runway kbenv install  # retrieves version from .kubectl-version

    $ runway kbenv run -- get namespace

"""

import subprocess
import sys

from runway.env_mgr.kbenv import KBEnvManager
from ..runway_command import RunwayCommand
from ...util import strip_leading_option_delim


class KBEnv(RunwayCommand):
    """Extend RunwayCommand with execution of kbenv."""

    SKIP_FIND_CONFIG = True

    def execute(self):
        """Execute kbenv."""
        if self._cli_arguments.get('install'):
            if self._cli_arguments.get('<kbenv-args>'):
                KBEnvManager().install(self._cli_arguments.get('<kbenv-args>')[0])
            else:
                KBEnvManager().install()
        elif self._cli_arguments.get('run'):
            cmd_line_args = strip_leading_option_delim(
                self._cli_arguments.get('<kbenv-args>', [])
            )
            kb_bin = KBEnvManager().install()
            sys.exit(subprocess.call([kb_bin] + cmd_line_args))
