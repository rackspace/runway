"""The test command."""

from ..modules_command import ModulesCommand

# THIS SHOULD BE A RUNWAY COMMAND?


class Test(ModulesCommand):
    """Extend Env with execute to run the test method."""

    def execute(self):
        """Run tests."""
        self.test()
