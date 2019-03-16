"""The destroy command."""
from .env import Env


class Destroy(Env):
    """Extend Env with execute to run the destroy method."""

    def execute(self):
        """Destroy deployments."""
        self.destroy()
