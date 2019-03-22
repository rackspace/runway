"""The gitclean command."""
from .env import Env


class GitClean(Env):
    """Extend Env with execute to run the gitclean method."""

    def execute(self):
        """Clean directory of files."""
        self.gitclean()
