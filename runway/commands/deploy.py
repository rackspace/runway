"""The deploy command."""
from .env import Env


class Deploy(Env):
    """Extend Env with execute to run the deploy method."""

    def execute(self):
        """Run deployments."""
        self.deploy()
