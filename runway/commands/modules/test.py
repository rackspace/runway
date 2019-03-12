"""The test command."""

from ..modules_command import ModulesCommand


class Test(ModulesCommand):
    """Extend ModulesCommand with execute to run the test method."""

    def execute(self):
        """Run tests."""
        self.test()
