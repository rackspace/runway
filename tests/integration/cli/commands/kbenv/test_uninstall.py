"""Test ``runway kbenv uninstall`` command."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from runway._cli import cli
from runway.env_mgr.kbenv import KB_VERSION_FILENAME, KBEnvManager

if TYPE_CHECKING:
    from pytest import LogCaptureFixture
    from pytest_mock import MockerFixture

LOGGER = "runway.cli.commands.kbenv"


@pytest.fixture(autouse=True, scope="function")
def patch_versions_dir(mocker: MockerFixture, tmp_path: Path) -> None:
    """Patch KBEnvManager.versions_dir."""
    mocker.patch.object(KBEnvManager, "versions_dir", tmp_path)


def test_kbenv_uninstall(cd_tmp_path: Path) -> None:
    """Test ``runway kbenv uninstall``."""
    version = "v1.21.0"
    version_dir = cd_tmp_path / version
    version_dir.mkdir()
    runner = CliRunner()
    result = runner.invoke(cli, ["kbenv", "uninstall", version])
    assert result.exit_code == 0
    assert not version_dir.exists()


def test_kbenv_uninstall_all(caplog: LogCaptureFixture, cd_tmp_path: Path) -> None:
    """Test ``runway kbenv uninstall --all``."""
    caplog.set_level(logging.INFO, logger=LOGGER)
    version_dirs = [cd_tmp_path / "v1.14.0", cd_tmp_path / "v1.21.0"]
    for v in version_dirs:
        v.mkdir()
    runner = CliRunner()
    result = runner.invoke(cli, ["kbenv", "uninstall", "--all"])
    assert result.exit_code == 0
    assert "uninstalling all versions of kubectl..." in caplog.messages
    assert "all versions of kubectl have been uninstalled" in caplog.messages
    assert all(not v.exists() for v in version_dirs)


def test_kbenv_uninstall_all_takes_precedence(caplog: LogCaptureFixture, cd_tmp_path: Path) -> None:
    """Test ``runway kbenv uninstall --all`` takes precedence over arg."""
    caplog.set_level(logging.INFO, logger=LOGGER)
    version_dirs = [cd_tmp_path / "v1.14.0", cd_tmp_path / "v1.21.0"]
    for v in version_dirs:
        v.mkdir()
    runner = CliRunner()
    result = runner.invoke(cli, ["kbenv", "uninstall", "0.13.0", "--all"])
    assert result.exit_code == 0
    assert "uninstalling all versions of kubectl..." in caplog.messages
    assert "all versions of kubectl have been uninstalled" in caplog.messages
    assert all(not v.exists() for v in version_dirs)


def test_kbenv_uninstall_all_none_installed(caplog: LogCaptureFixture, cd_tmp_path: Path) -> None:
    """Test ``runway kbenv uninstall --all`` none installed."""
    caplog.set_level(logging.INFO, logger=LOGGER)
    runner = CliRunner()
    result = runner.invoke(cli, ["kbenv", "uninstall", "--all"])
    assert result.exit_code == 0
    assert "uninstalling all versions of kubectl..." in caplog.messages
    assert "all versions of kubectl have been uninstalled" in caplog.messages


def test_kbenv_uninstall_arg_takes_precedence(cd_tmp_path: Path) -> None:
    """Test ``runway kbenv uninstall`` arg takes precedence over file."""
    version = "v1.21.0"
    version_dir = cd_tmp_path / version
    version_dir.mkdir()
    (cd_tmp_path / KB_VERSION_FILENAME).write_text("v1.14.0")
    runner = CliRunner()
    result = runner.invoke(cli, ["kbenv", "uninstall", version])
    assert result.exit_code == 0
    assert not version_dir.exists()


def test_kbenv_uninstall_no_version(caplog: LogCaptureFixture, cd_tmp_path: Path) -> None:
    """Test ``runway kbenv uninstall`` no version."""
    caplog.set_level(logging.ERROR, logger=LOGGER)
    runner = CliRunner()
    result = runner.invoke(cli, ["kbenv", "uninstall"])
    assert result.exit_code != 0
    assert "version not specified" in caplog.messages


def test_kbenv_uninstall_not_installed(cd_tmp_path: Path) -> None:
    """Test ``runway kbenv uninstall`` not installed."""
    runner = CliRunner()
    result = runner.invoke(cli, ["kbenv", "uninstall", "1.21.0"])
    assert result.exit_code != 0


def test_kbenv_uninstall_version_file(cd_tmp_path: Path) -> None:
    """Test ``runway kbenv uninstall`` version file."""
    version = "v1.21.0"
    version_dir = cd_tmp_path / version
    version_dir.mkdir()
    (cd_tmp_path / KB_VERSION_FILENAME).write_text(version)
    runner = CliRunner()
    result = runner.invoke(cli, ["kbenv", "uninstall"])
    assert result.exit_code == 0
    assert not version_dir.exists()
