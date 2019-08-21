"""The tfenv command."""

import subprocess
import sys

from runway.tfenv import TFEnvManager
from ..runway_command import RunwayCommand
from ...util import strip_leading_option_delim


class TFEnv(RunwayCommand):
    """Extend RunwayCommand with execution of tfenv."""

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
