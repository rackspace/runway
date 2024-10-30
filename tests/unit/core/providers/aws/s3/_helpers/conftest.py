"""Pytest fixtures and plugins."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from typing_extensions import TypedDict

if TYPE_CHECKING:
    from pathlib import Path


class LocalFiles(TypedDict):
    files: list[Path]
    local_dir: Path
    local_file: Path
    tmp_path: Path


@pytest.fixture
def loc_files(tmp_path: Path) -> LocalFiles:
    """Fixture for creating local files."""
    file0 = tmp_path / "some_directory" / "text0.txt"
    file0.parent.mkdir()
    file0.write_text("This is a test.")
    file1 = tmp_path / "another_directory" / "text1.txt"
    file1.parent.mkdir()
    file1.write_text("This is a test.")
    return LocalFiles(
        files=[file0, file1, file1.parent, file0.parent],
        local_dir=file0.parent,
        local_file=file0,
        tmp_path=tmp_path,
    )
