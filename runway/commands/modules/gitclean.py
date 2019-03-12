"""The gitclean command."""

from ..modules_command import ModulesCommand

# THIS SHOULD BE RUNWAY COMMAND?


class GitClean(ModulesCommand):
    """Extend Env with execute to run the gitclean method."""

    def execute(self):
        """Clean directory of files."""
        self.gitclean()
