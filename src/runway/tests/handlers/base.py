"""Base module for test handlers."""
import os
from typing import Dict, Any, List  # pylint: disable=unused-import


class TestHandler(object):
    """Base class for test handlers."""

    @classmethod
    def handle(cls, name, args):
        # type: (str, Dict[str, Any]) -> None
        """Redefine in subclass."""
        raise NotImplementedError()

    @staticmethod
    def get_dirs(provided_path):
        # type: (str) -> List[str]
        """Return list of directories."""
        repo_dirs = next(os.walk(provided_path))[1]
        if '.git' in repo_dirs:
            repo_dirs.remove('.git')  # not relevant for any repo operations
        return repo_dirs
