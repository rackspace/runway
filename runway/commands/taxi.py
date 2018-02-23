"""The taxi command."""
from .env import Env


class Taxi(Env):
    """Extend Env with execute to run the plan method."""

    def execute(self):
        """Generate plans."""
        self.plan()
