"""The taxi command."""
from ..modules_command import ModulesCommand


class Taxi(ModulesCommand):
    """Extend Env with execute to run the plan method."""

    def execute(self):
        """Generate plans."""
        self.plan()
