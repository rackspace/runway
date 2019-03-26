"""The takeoff command."""
from ..modules_command import ModulesCommand


class Takeoff(ModulesCommand):
    """Extend ModulesCommand with execute to run the deploy method."""

    def execute(self):
        """Run deployments."""
        self.deploy()
