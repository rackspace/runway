"""Test ``runway tfenv uninstall`` command."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from runway._cli import cli
from runway.env_mgr.tfenv import TF_VERSION_FILENAME

if TYPE_CHECKING:
    from pathlib import Path

    import pytest
    from click.testing import CliRunner

LOGGER = "runway.cli.commands.tfenv"


def test_tfenv_uninstall(cli_runner: CliRunner, versions_dir: Path) -> None:
    """Test ``runway tfenv uninstall``."""
    version = "1.0.0"
    version_dir = versions_dir / version
    version_dir.mkdir()
    result = cli_runner.invoke(cli, ["tfenv", "uninstall", "1.0.0"])
    assert result.exit_code == 0
    assert not version_dir.exists()


def test_tfenv_uninstall_all(
    caplog: pytest.LogCaptureFixture, cli_runner: CliRunner, versions_dir: Path
) -> None:
    """Test ``runway tfenv uninstall --all``."""
    caplog.set_level(logging.INFO, logger=LOGGER)
    version_dirs = [versions_dir / "0.12.0", versions_dir / "1.0.0"]
    for v in version_dirs:
        v.mkdir()
    result = cli_runner.invoke(cli, ["tfenv", "uninstall", "--all"])
    assert result.exit_code == 0
    assert "uninstalling all versions of Terraform..." in caplog.messages
    assert "all versions of Terraform have been uninstalled" in caplog.messages
    assert all(not v.exists() for v in version_dirs)


def test_tfenv_uninstall_all_takes_precedence(
    caplog: pytest.LogCaptureFixture, cli_runner: CliRunner, versions_dir: Path
) -> None:
    """Test ``runway tfenv uninstall --all`` takes precedence over arg."""
    caplog.set_level(logging.INFO, logger=LOGGER)
    version_dirs = [versions_dir / "0.12.0", versions_dir / "1.0.0"]
    for v in version_dirs:
        v.mkdir()
    result = cli_runner.invoke(cli, ["tfenv", "uninstall", "0.13.0", "--all"])
    assert result.exit_code == 0
    assert "uninstalling all versions of Terraform..." in caplog.messages
    assert "all versions of Terraform have been uninstalled" in caplog.messages
    assert all(not v.exists() for v in version_dirs)


def test_tfenv_uninstall_all_none_installed(
    caplog: pytest.LogCaptureFixture, cli_runner: CliRunner
) -> None:
    """Test ``runway tfenv uninstall --all`` none installed."""
    caplog.set_level(logging.INFO, logger=LOGGER)
    result = cli_runner.invoke(cli, ["tfenv", "uninstall", "--all"])
    assert result.exit_code == 0
    assert "uninstalling all versions of Terraform..." in caplog.messages
    assert "all versions of Terraform have been uninstalled" in caplog.messages


def test_tfenv_uninstall_arg_takes_precedence(
    cd_tmp_path: Path, cli_runner: CliRunner, versions_dir: Path
) -> None:
    """Test ``runway tfenv uninstall`` arg takes precedence over file."""
    version = "1.0.0"
    version_dir = versions_dir / version
    version_dir.mkdir()
    (cd_tmp_path / TF_VERSION_FILENAME).write_text("0.12.0")
    result = cli_runner.invoke(cli, ["tfenv", "uninstall", "1.0.0"])
    assert result.exit_code == 0
    assert not version_dir.exists()


def test_tfenv_uninstall_no_version(
    caplog: pytest.LogCaptureFixture, cli_runner: CliRunner
) -> None:
    """Test ``runway tfenv uninstall`` no version."""
    caplog.set_level(logging.ERROR, logger=LOGGER)
    result = cli_runner.invoke(cli, ["tfenv", "uninstall"])
    assert result.exit_code != 0
    assert "version not specified" in caplog.messages


def test_tfenv_uninstall_not_installed(cli_runner: CliRunner) -> None:
    """Test ``runway tfenv uninstall`` not installed."""
    assert cli_runner.invoke(cli, ["tfenv", "uninstall", "1.0.0"]).exit_code != 0


def test_tfenv_uninstall_version_file(
    cd_tmp_path: Path, cli_runner: CliRunner, versions_dir: Path
) -> None:
    """Test ``runway tfenv uninstall`` version file."""
    version = "1.0.0"
    version_dir = versions_dir / version
    version_dir.mkdir()
    (cd_tmp_path / TF_VERSION_FILENAME).write_text(version)
    result = cli_runner.invoke(cli, ["tfenv", "uninstall"])
    assert result.exit_code == 0
    assert not version_dir.exists()
