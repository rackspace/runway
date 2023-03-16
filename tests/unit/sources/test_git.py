"""Tests for the Source type object."""

# pyright: basic
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from runway.sources.git import Git

if TYPE_CHECKING:
    from pathlib import Path

LOGGER = logging.getLogger("runway")


class TestGit:
    """Tests for the Source type object."""

    def test_fetch_returns_directory_string(self, cd_tmp_path: Path) -> None:
        """Ensure a directory string is returned."""
        result = Git(
            cache_dir=cd_tmp_path,
            location="/",
            options={},
            uri="https://github.com/onicagroup/runway.git",
        ).fetch()
        assert result.parent == cd_tmp_path
        assert "onicagroup_runway" in result.name

    def test_sanitize_git_path(self) -> None:
        """Ensure git path is property sanitized."""
        path = Git.sanitize_git_path("https://github.com/onicagroup/runway.git")
        assert path == "github.com_onicagroup_runway"
