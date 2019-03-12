"""The takeoff command."""
from ..modules_command import ModulesCommand


class Takeoff(ModulesCommand):
    """Extend Env with execute to run the deploy method."""

    def execute(self):
        """Run deployments."""
        self.deploy()
