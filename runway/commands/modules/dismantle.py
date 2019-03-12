"""The dismantle command."""
from ..modules_command import ModulesCommand


class Dismantle(ModulesCommand):
    """Extend ModulesCommand with execute to run the destroy method."""

    def execute(self):
        """Destroy deployments."""
        self.destroy()
