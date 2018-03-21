"""The dismantle command."""
from .env import Env


class Dismantle(Env):
    """Extend Env with execute to run the destroy method."""

    def execute(self):
        """Destroy deployments."""
        self.destroy()
