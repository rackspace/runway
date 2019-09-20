"""The whichenv command."""
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
            self.runway_config.get('ignore_git_branch', False)
        ))
