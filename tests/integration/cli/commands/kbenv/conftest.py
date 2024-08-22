"""Pytest fixtures and plugins."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockFixture


@pytest.fixture(autouse=True)
def versions_dir(cd_tmp_path: Path, mocker: MockFixture) -> Path:
    """Patches TFEnvManager.versions_dir."""
    path = cd_tmp_path / "versions"
    path.mkdir(exist_ok=True)
    mocker.patch("runway._cli.commands._kbenv._install.KBEnvManager.versions_dir", path)
    mocker.patch("runway._cli.commands._kbenv._list.KBEnvManager.versions_dir", path)
    mocker.patch("runway._cli.commands._kbenv._run.KBEnvManager.versions_dir", path)
    mocker.patch("runway._cli.commands._kbenv._uninstall.KBEnvManager.versions_dir", path)
    return path
