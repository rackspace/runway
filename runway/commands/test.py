"""The test command."""
from .env import Env


class Test(Env):
    """Extend Env with execute to run the test method."""

    def execute(self):
        """Run tests."""
        self.test()
