"""The kbenv command."""

import subprocess
import sys

from runway.kbenv import KBEnvManager
from ..runway_command import RunwayCommand
from ...util import strip_leading_option_delim


class KBEnv(RunwayCommand):
    """Extend RunwayCommand with execution of kbenv."""

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
