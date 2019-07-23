"""The deploy command."""
from ..modules_command import ModulesCommand


class Deploy(ModulesCommand):
    """Extend ModulesCommand with execute to run the deploy method."""

    def execute(self):
        """Run deployments."""
        self.run(deployments=None, command='deploy')
