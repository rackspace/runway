"""Test ``runway kbenv uninstall`` command."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from runway._cli import cli
from runway.env_mgr.kbenv import KB_VERSION_FILENAME

if TYPE_CHECKING:
    from pathlib import Path

    import pytest
    from click.testing import CliRunner

LOGGER = "runway.cli.commands.kbenv"


def test_kbenv_uninstall(cli_runner: CliRunner, versions_dir: Path) -> None:
    """Test ``runway kbenv uninstall``."""
    version = "v1.21.0"
    version_dir = versions_dir / version
    version_dir.mkdir()
    result = cli_runner.invoke(cli, ["kbenv", "uninstall", version])
    assert result.exit_code == 0
    assert not version_dir.exists()


def test_kbenv_uninstall_all(
    caplog: pytest.LogCaptureFixture, cli_runner: CliRunner, versions_dir: Path
) -> None:
    """Test ``runway kbenv uninstall --all``."""
    caplog.set_level(logging.INFO, logger=LOGGER)
    version_dirs = [versions_dir / "v1.14.0", versions_dir / "v1.21.0"]
    for v in version_dirs:
        v.mkdir()
    result = cli_runner.invoke(cli, ["kbenv", "uninstall", "--all"])
    assert result.exit_code == 0
    assert "uninstalling all versions of kubectl..." in caplog.messages
    assert "all versions of kubectl have been uninstalled" in caplog.messages
    assert all(not v.exists() for v in version_dirs)


def test_kbenv_uninstall_all_takes_precedence(
    caplog: pytest.LogCaptureFixture, cli_runner: CliRunner, versions_dir: Path
) -> None:
    """Test ``runway kbenv uninstall --all`` takes precedence over arg."""
    caplog.set_level(logging.INFO, logger=LOGGER)
    version_dirs = [versions_dir / "v1.14.0", versions_dir / "v1.21.0"]
    for v in version_dirs:
        v.mkdir()
    result = cli_runner.invoke(cli, ["kbenv", "uninstall", "0.13.0", "--all"])
    assert result.exit_code == 0
    assert "uninstalling all versions of kubectl..." in caplog.messages
    assert "all versions of kubectl have been uninstalled" in caplog.messages
    assert all(not v.exists() for v in version_dirs)


def test_kbenv_uninstall_all_none_installed(
    caplog: pytest.LogCaptureFixture, cli_runner: CliRunner
) -> None:
    """Test ``runway kbenv uninstall --all`` none installed."""
    caplog.set_level(logging.INFO, logger=LOGGER)
    result = cli_runner.invoke(cli, ["kbenv", "uninstall", "--all"])
    assert result.exit_code == 0
    assert "uninstalling all versions of kubectl..." in caplog.messages
    assert "all versions of kubectl have been uninstalled" in caplog.messages


def test_kbenv_uninstall_arg_takes_precedence(
    cd_tmp_path: Path, cli_runner: CliRunner, versions_dir: Path
) -> None:
    """Test ``runway kbenv uninstall`` arg takes precedence over file."""
    version = "v1.21.0"
    version_dir = versions_dir / version
    version_dir.mkdir()
    (cd_tmp_path / KB_VERSION_FILENAME).write_text("v1.14.0")
    result = cli_runner.invoke(cli, ["kbenv", "uninstall", version])
    assert result.exit_code == 0
    assert not version_dir.exists()


def test_kbenv_uninstall_no_version(
    caplog: pytest.LogCaptureFixture, cli_runner: CliRunner
) -> None:
    """Test ``runway kbenv uninstall`` no version."""
    caplog.set_level(logging.ERROR, logger=LOGGER)
    result = cli_runner.invoke(cli, ["kbenv", "uninstall"])
    assert result.exit_code != 0
    assert "version not specified" in caplog.messages


def test_kbenv_uninstall_not_installed(cli_runner: CliRunner) -> None:
    """Test ``runway kbenv uninstall`` not installed."""
    assert cli_runner.invoke(cli, ["kbenv", "uninstall", "1.21.0"]).exit_code != 0


def test_kbenv_uninstall_version_file(
    cd_tmp_path: Path, cli_runner: CliRunner, versions_dir: Path
) -> None:
    """Test ``runway kbenv uninstall`` version file."""
    version = "v1.21.0"
    version_dir = versions_dir / version
    version_dir.mkdir()
    (cd_tmp_path / KB_VERSION_FILENAME).write_text(version)
    result = cli_runner.invoke(cli, ["kbenv", "uninstall"])
    assert result.exit_code == 0
    assert not version_dir.exists()
