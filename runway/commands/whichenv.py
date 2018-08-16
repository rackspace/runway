"""The whichenv command."""
from __future__ import print_function

import logging
import os

from .env import Env, get_env


class WhichEnv(Env):
    """Extend Env with execute to run the get_env method."""

    def execute(self):
        """Output environment name."""
        # Disable other runway logging so the only response is the env name
        logging.getLogger('runway').setLevel(logging.ERROR)

        # This may be invoked from a module directory in an environment;
        # account for that here if necessary
        if not os.path.isfile('runway.yml'):
            self.env_root = os.path.dirname(os.getcwd())
            self.runway_config_path = os.path.join(self.env_root, 'runway.yml')

        print(get_env(
            self.env_root,
            self.runway_config.get('ignore_git_branch',
                                   False)))
