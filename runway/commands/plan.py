"""The plan command."""
from .env import Env


class Plan(Env):
    """Extend Env with execute to run the plan method."""

    def execute(self):
        """Generate plans."""
        self.plan()
