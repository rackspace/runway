"""The plan command."""
from ..modules_command import ModulesCommand


class Plan(ModulesCommand):
    """Extend ModulesCommand with execute to run the plan method."""

    def execute(self):
        """Generate plans."""
        self.plan()
