"""Manage versions and execute `Terraform`_ commands.

Runway's built-in Terraform version management allows for long-term
stability of Terraform executions. Define a ``.terraform-version`` file
in your Terraform module and that version will be automatically
downloaded & used during Runway operations.

The ``tfenv`` subcommand supplements this functionality in 2 ways:

* The ``install`` option will download Terraform (e.g. for
  pre-seeding a deployment system)
* The ``run`` option will execute arbitrary Terraform commands

Examples:
  .. code-block:: shell

    $ runway tfenv install 0.12.1
    $ runway tfenv install  # retrieves version from .terraform-version

    $ runway tfenv run -- workspace list

"""

import subprocess
import sys

from runway.env_mgr.tfenv import TFEnvManager
from ..runway_command import RunwayCommand
from ...util import strip_leading_option_delim


class TFEnv(RunwayCommand):
    """Extend RunwayCommand with execution of tfenv."""

    SKIP_FIND_CONFIG = True

    def execute(self):
        """Execute tfenv."""
        if self._cli_arguments.get('install'):
            if self._cli_arguments.get('<tfenv-args>'):
                TFEnvManager().install(self._cli_arguments.get('<tfenv-args>')[0])
            else:
                TFEnvManager().install()
        elif self._cli_arguments.get('run'):
            cmd_line_args = strip_leading_option_delim(
                self._cli_arguments.get('<tfenv-args>', [])
            )
            tf_bin = TFEnvManager().install()
            sys.exit(subprocess.call([tf_bin] + cmd_line_args))
