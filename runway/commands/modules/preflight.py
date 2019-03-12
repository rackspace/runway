"""The preflight command."""
from ..modules_command import ModulesCommand


class Preflight(ModulesCommand):
    """Extend ModulesCommand with execute to run the test method."""

    def execute(self):
        """Run tests."""
        self.test()
