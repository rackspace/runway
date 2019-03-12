"""The gitclean command."""

from ..modules_command import ModulesCommand


class GitClean(ModulesCommand):
    """Extend ModulesCommand with execute to run the gitclean method."""

    def execute(self):
        """Clean directory of files."""
        self.gitclean()
