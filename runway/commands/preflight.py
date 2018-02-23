"""The preflight command."""
from .env import Env


class Preflight(Env):
    """Extend Env with execute to run the test method."""

    def execute(self):
        """Run tests."""
        self.test()
