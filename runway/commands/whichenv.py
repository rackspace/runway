"""The show-env command."""
from __future__ import print_function

import logging
import os

from .base import Base


class WhichEnv(Base):
    """Extend Base with execute to run the get_env method."""

    def execute(self):
        """Output environment name."""
        # Disable other runway logging so the only response is the env name
        logging.getLogger('runway').setLevel(logging.ERROR)

        # This may be invoked from a module directory in an environment;
        # account for that here if necessary
        if not os.path.isfile('runway.yml'):
            self.runway_config_path = os.path.join(
                os.path.dirname(os.getcwd()),
                'runway.yml')

        print(self.get_env())
