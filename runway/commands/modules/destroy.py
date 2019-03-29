"""The destroy command."""
from ..modules_command import ModulesCommand


class Destroy(ModulesCommand):
    """Extend ModulesCommand with execute to run the destroy method."""

    def execute(self):
        """Destroy deployments."""
        self.run(deployments=None, command='destroy')
