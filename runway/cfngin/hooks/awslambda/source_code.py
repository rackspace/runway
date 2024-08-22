"""Source code."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import igittigitt

from runway.compat import cached_property
from runway.utils import FileHash

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from _typeshed import StrPath

LOGGER = logging.getLogger(__name__)


class SourceCode:
    """Source code iterable."""

    gitignore_filter: igittigitt.IgnoreParser
    """Filter to use when zipping dependencies.
    If file/folder matches the filter, it should be ignored.

    """

    project_root: Path
    """Top-level directory containing the project metadata files and source code root directory.
    The value can be the same as ``root_directory``.
    If it is not, it must be a parent of ``root_directory``.

    """

    root_directory: Path
    """The root directory containing the source code."""

    def __init__(
        self,
        root_directory: StrPath,
        *,
        gitignore_filter: igittigitt.IgnoreParser | None = None,
        include_files_in_hash: Sequence[Path] | None = None,
        project_root: StrPath | None = None,
    ) -> None:
        """Instantiate class.

        Args:
            root_directory: The root directory containing the source code.
            gitignore_filter: Object that has been pre-populated with
                rules/patterns to determine if a file should be ignored.
            include_files_in_hash: Files that should be included in hash
                calculation even if they are filtered by gitignore (e.g.
                ``poetry.lock``).
            project_root: Optional project root if the source code is located
                within a larger project. This should only be used if the
                contents of value of ``include_files_in_hash`` contains paths
                that exist outside of the root directory. If this is provided,
                it must be a parent of the root directory.

        """
        self._include_files_in_hash = include_files_in_hash or []
        self.gitignore_filter = gitignore_filter or igittigitt.IgnoreParser()
        self.root_directory = (
            root_directory if isinstance(root_directory, Path) else Path(root_directory)
        )
        self.project_root = (  # defaults to root_directory if project_root not provided
            project_root
            if isinstance(project_root, Path)
            else (Path(project_root) if project_root else self.root_directory)
        )

        if not gitignore_filter:
            self.gitignore_filter.parse_rule_files(self.root_directory)
            self.gitignore_filter.add_rule(".git/", self.root_directory)
            self.gitignore_filter.add_rule(".gitignore", self.root_directory)

    @cached_property
    def md5_hash(self) -> str:
        """Calculate the md5 hash of the directory contents.

        This can be resource intensive depending on the size of the project.

        """
        sorted_files = list(self.sorted())
        for include_file in self._include_files_in_hash:
            if include_file not in sorted_files:
                sorted_files.append(include_file)
        file_hash = FileHash(hashlib.md5())  # noqa: S324
        file_hash.add_files(sorted(sorted_files), relative_to=self.project_root)
        return file_hash.hexdigest

    def add_filter_rule(self, pattern: str) -> None:
        """Add rule to ignore filter.

        Args:
            pattern: The gitignore pattern to add to the filter.

        """
        self.gitignore_filter.add_rule(pattern=pattern, base_path=self.root_directory)

    def sorted(self, *, reverse: bool = False) -> list[Path]:
        """Sorted list of source code files.

        Args:
            reverse: Sort the list in reverse.

        Returns:
            Sorted list of source code files excluding those that match the
            ignore filter.

        """
        return sorted(self, reverse=reverse)

    def __eq__(self, other: object) -> bool:
        """Compare if self is equal to another object."""
        if isinstance(other, SourceCode):
            return self.root_directory == other.root_directory
        return False

    def __fspath__(self) -> str | bytes:
        """Return the file system path representation of the object."""
        return str(self.root_directory)

    def __iter__(self) -> Iterator[Path]:
        """Iterate over the source code files.

        Yields:
            Files that do not match the ignore filter. Order in arbitrary.

        """
        for child in self.root_directory.rglob("*"):
            if child.is_dir():
                continue  # ignore directories
            if self.gitignore_filter.match(child):
                continue  # ignore files that match the filter
            yield child

    def __str__(self) -> str:
        """Return the string representation of the object."""
        return str(self.root_directory)

    def __truediv__(self, other: StrPath) -> Path:
        """Create a new path object from source code's root directory."""
        return self.root_directory / other
