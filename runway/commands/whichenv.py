"""The show-env command."""
from __future__ import print_function

import logging

from .base import Base


class WhichEnv(Base):
    """Extend Base with execute to run the get_env method."""

    def execute(self):
        """Output environment name."""
        # Disable other runway logging so the only response is the env name
        logging.getLogger('runway').setLevel(logging.ERROR)
        print(self.get_env())
