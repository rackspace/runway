"""AWS Lambda Python Deployment Package."""

from __future__ import annotations

from typing import TYPE_CHECKING

from igittigitt import IgnoreParser

from .....compat import cached_property
from ..deployment_package import DeploymentPackage

if TYPE_CHECKING:
    from pathlib import Path

    from . import PythonProject


class PythonDeploymentPackage(DeploymentPackage["PythonProject"]):
    """AWS Lambda Python Deployment Package."""

    project: PythonProject

    @cached_property
    def gitignore_filter(self) -> IgnoreParser | None:
        """Filter to use when zipping dependencies.

        This should be overridden by subclasses if a filter should be used.

        """
        if self.project.args.slim:
            gitignore_filter = IgnoreParser()
            gitignore_filter.add_rule("**/*.dist-info*", self.project.dependency_directory)
            gitignore_filter.add_rule("**/*.py[c|d|i|o]", self.project.dependency_directory)
            gitignore_filter.add_rule("**/__pycache__*", self.project.dependency_directory)
            if self.project.args.strip:
                gitignore_filter.add_rule("**/*.so", self.project.dependency_directory)
            return gitignore_filter
        return None

    @staticmethod
    def insert_layer_dir(file_path: Path, relative_to: Path) -> Path:
        """Insert ``python`` directory into local file path for layer archive.

        Args:
            file_path: Path to local file.
            relative_to: Path to a directory that the file_path will be relative
                to in the deployment package.

        """
        return relative_to / f"python/{file_path.relative_to(relative_to)}"
