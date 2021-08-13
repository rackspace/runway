"""Utility functions for website build/upload."""
from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Iterable, List, Optional, Union, cast

import zgitignore

from ....utils import FileHash, change_dir

if TYPE_CHECKING:
    from _typeshed import StrPath

LOGGER = logging.getLogger(__name__)


def calculate_hash_of_files(files: Iterable[StrPath], root: Path) -> str:
    """Return a hash of all of the given files at the given root.

    Args:
        files: file names to include in the hash calculation, relative to ``root``.
        root: base directory to analyze files in.

    Returns:
        A hash of the hashes of the given files.

    """
    file_hash = FileHash(hashlib.md5())
    file_hash.add_files(sorted(str(f) for f in files), relative_to=root)
    return file_hash.hexdigest


def get_hash_of_files(
    root_path: Path,
    directories: Optional[List[Dict[str, Union[List[str], str]]]] = None,
) -> str:
    """Generate md5 hash of files."""
    if not directories:
        directories = [{"path": "./"}]

    files_to_hash: List[StrPath] = []
    for i in directories:
        ignorer = get_ignorer(
            root_path / cast(str, i["path"]), cast(List[str], i.get("exclusions"))
        )

        with change_dir(root_path):
            for root, dirs, files in os.walk(cast(str, i["path"]), topdown=True):
                if (root != "./") and ignorer.is_ignored(root, True):
                    dirs[:] = []  # type: ignore
                    files[:] = []  # type: ignore
                else:
                    for filename in files:
                        filepath = os.path.join(root, filename)
                        if not ignorer.is_ignored(filepath):
                            files_to_hash.append(Path(filepath).resolve())

    return calculate_hash_of_files(files_to_hash, root_path)


def get_ignorer(
    path: Path, additional_exclusions: Optional[List[str]] = None
) -> zgitignore.ZgitIgnore:
    """Create ignorer with directory gitignore file."""
    ignorefile = zgitignore.ZgitIgnore()
    gitignore_file = path / ".gitignore"
    if gitignore_file.is_file():
        ignorefile.add_patterns(gitignore_file.read_text().splitlines())

    if additional_exclusions:
        ignorefile.add_patterns(additional_exclusions)

    return ignorefile
