"""The takeoff command."""
from .env import Env


class Takeoff(Env):
    """Extend Env with execute to run the deploy method."""

    def execute(self):
        """Run deployments."""
        self.deploy()
