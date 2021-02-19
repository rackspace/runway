"""Base module for test handlers."""
from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, Dict, List, Union

if TYPE_CHECKING:
    from ...config.components.runway.base import ConfigProperty


class TestHandler:
    """Base class for test handlers."""

    @classmethod
    def handle(cls, name: str, args: Union[ConfigProperty, Dict[str, Any]]) -> None:
        """Redefine in subclass."""
        raise NotImplementedError()

    @staticmethod
    def get_dirs(provided_path: str) -> List[str]:
        """Return list of directories."""
        repo_dirs = next(os.walk(provided_path))[1]
        if ".git" in repo_dirs:
            repo_dirs.remove(".git")  # not relevant for any repo operations
        return repo_dirs
