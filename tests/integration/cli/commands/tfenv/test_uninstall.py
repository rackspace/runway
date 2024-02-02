"""Test ``runway tfenv uninstall`` command."""

# pylint: disable=unused-argument
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from runway._cli import cli
from runway.env_mgr.tfenv import TF_VERSION_FILENAME, TFEnvManager

if TYPE_CHECKING:
    from pytest import LogCaptureFixture
    from pytest_mock import MockerFixture

LOGGER = "runway.cli.commands.tfenv"


@pytest.fixture(autouse=True, scope="function")
def patch_versions_dir(mocker: MockerFixture, tmp_path: Path) -> None:
    """Patch TFEnvManager.versions_dir."""
    mocker.patch.object(TFEnvManager, "versions_dir", tmp_path)


def test_tfenv_uninstall(cd_tmp_path: Path) -> None:
    """Test ``runway tfenv uninstall``."""
    version = "1.0.0"
    version_dir = cd_tmp_path / version
    version_dir.mkdir()
    runner = CliRunner()
    result = runner.invoke(cli, ["tfenv", "uninstall", "1.0.0"])
    assert result.exit_code == 0
    assert not version_dir.exists()


def test_tfenv_uninstall_all(caplog: LogCaptureFixture, cd_tmp_path: Path) -> None:
    """Test ``runway tfenv uninstall --all``."""
    caplog.set_level(logging.INFO, logger=LOGGER)
    version_dirs = [cd_tmp_path / "0.12.0", cd_tmp_path / "1.0.0"]
    for v in version_dirs:
        v.mkdir()
    runner = CliRunner()
    result = runner.invoke(cli, ["tfenv", "uninstall", "--all"])
    assert result.exit_code == 0
    assert "uninstalling all versions of Terraform..." in caplog.messages
    assert "all versions of Terraform have been uninstalled" in caplog.messages
    assert all(not v.exists() for v in version_dirs)


def test_tfenv_uninstall_all_takes_precedence(
    caplog: LogCaptureFixture, cd_tmp_path: Path
) -> None:
    """Test ``runway tfenv uninstall --all`` takes precedence over arg."""
    caplog.set_level(logging.INFO, logger=LOGGER)
    version_dirs = [cd_tmp_path / "0.12.0", cd_tmp_path / "1.0.0"]
    for v in version_dirs:
        v.mkdir()
    runner = CliRunner()
    result = runner.invoke(cli, ["tfenv", "uninstall", "0.13.0", "--all"])
    assert result.exit_code == 0
    assert "uninstalling all versions of Terraform..." in caplog.messages
    assert "all versions of Terraform have been uninstalled" in caplog.messages
    assert all(not v.exists() for v in version_dirs)


def test_tfenv_uninstall_all_none_installed(
    caplog: LogCaptureFixture, cd_tmp_path: Path
) -> None:
    """Test ``runway tfenv uninstall --all`` none installed."""
    caplog.set_level(logging.INFO, logger=LOGGER)
    runner = CliRunner()
    result = runner.invoke(cli, ["tfenv", "uninstall", "--all"])
    assert result.exit_code == 0
    assert "uninstalling all versions of Terraform..." in caplog.messages
    assert "all versions of Terraform have been uninstalled" in caplog.messages


def test_tfenv_uninstall_arg_takes_precedence(cd_tmp_path: Path) -> None:
    """Test ``runway tfenv uninstall`` arg takes precedence over file."""
    version = "1.0.0"
    version_dir = cd_tmp_path / version
    version_dir.mkdir()
    (cd_tmp_path / TF_VERSION_FILENAME).write_text("0.12.0")
    runner = CliRunner()
    result = runner.invoke(cli, ["tfenv", "uninstall", "1.0.0"])
    assert result.exit_code == 0
    assert not version_dir.exists()


def test_tfenv_uninstall_no_version(
    caplog: LogCaptureFixture, cd_tmp_path: Path
) -> None:
    """Test ``runway tfenv uninstall`` no version."""
    caplog.set_level(logging.ERROR, logger=LOGGER)
    runner = CliRunner()
    result = runner.invoke(cli, ["tfenv", "uninstall"])
    assert result.exit_code != 0
    assert "version not specified" in caplog.messages


def test_tfenv_uninstall_not_installed(cd_tmp_path: Path) -> None:
    """Test ``runway tfenv uninstall`` not installed."""
    runner = CliRunner()
    result = runner.invoke(cli, ["tfenv", "uninstall", "1.0.0"])
    assert result.exit_code != 0


def test_tfenv_uninstall_version_file(cd_tmp_path: Path) -> None:
    """Test ``runway tfenv uninstall`` version file."""
    version = "1.0.0"
    version_dir = cd_tmp_path / version
    version_dir.mkdir()
    (cd_tmp_path / TF_VERSION_FILENAME).write_text(version)
    runner = CliRunner()
    result = runner.invoke(cli, ["tfenv", "uninstall"])
    assert result.exit_code == 0
    assert not version_dir.exists()
