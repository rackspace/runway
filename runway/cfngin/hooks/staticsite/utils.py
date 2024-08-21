"""Utility functions for website build/upload."""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, cast

import igittigitt

from ....utils import FileHash, change_dir

if TYPE_CHECKING:
    from collections.abc import Iterable

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
    file_hash = FileHash(hashlib.md5())  # noqa: S324
    file_hash.add_files(sorted(str(f) for f in files), relative_to=root)
    return file_hash.hexdigest


def get_hash_of_files(
    root_path: Path,
    directories: list[dict[str, list[str] | str | None]] | None = None,
) -> str:
    """Generate md5 hash of files.

    Args:
        root_path: Base directory where all paths will be relative to.
            This should already be resolve to an absolute path.
        directories: List of mappings that describe the paths to hash and files
            to exclude.

    """
    directories = directories or [{"path": "./"}]

    files_to_hash: list[StrPath] = []
    for i in directories:
        gitignore = get_ignorer(
            root_path / cast(str, i["path"]),
            cast("list[str] | None", i.get("exclusions")),
        )

        with change_dir(root_path):
            for root, dirs, files in os.walk(cast(str, i["path"]), topdown=True):
                sub_root = Path(root).resolve()
                if root != "./" and gitignore.match(sub_root):
                    dirs[:] = []
                    files[:] = []
                else:
                    for filename in files:
                        filepath = sub_root / filename
                        if not gitignore.match(filepath):
                            files_to_hash.append(filepath)

    return calculate_hash_of_files(files_to_hash, root_path)


def get_ignorer(
    path: Path, additional_exclusions: list[str] | None = None
) -> igittigitt.IgnoreParser:
    """Create gitignore filter from directory ``.gitignore`` file.

    Args:
        path: Top-level directory that the gitignore filter will be created for.
            This directory and it's subdirectories will be searched for
            ``.gitignore`` files to use.
        additional_exclusions: Additional gitignore patterns to add.

    """
    additional_exclusions = additional_exclusions or []
    gitignore = igittigitt.IgnoreParser()
    gitignore.parse_rule_files(path)
    for rule in additional_exclusions:
        gitignore.add_rule(rule, path)
    return gitignore
