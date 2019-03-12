"""The deploy command."""
from ..modules_command import ModulesCommand


class Deploy(ModulesCommand):
    """Extend Env with execute to run the deploy method."""

    def execute(self):
        """Run deployments."""
        self.deploy()
