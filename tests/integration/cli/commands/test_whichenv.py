"""Test ``runway whichenv``."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import yaml
from click.testing import CliRunner

from runway._cli import cli

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_whichenv(caplog: pytest.LogCaptureFixture, cd_tmp_path: Path) -> None:
    """Test ``runway whichenv``."""
    caplog.set_level(logging.DEBUG, logger="runway")
    runway_yml = cd_tmp_path / "runway.yml"
    runway_yml.write_text(yaml.safe_dump({"deployments": [], "ignore_git_branch": True}))
    runner = CliRunner()
    result = runner.invoke(cli, ["whichenv"], env={})
    assert result.exit_code == 0
    assert result.output == cd_tmp_path.name + "\n"


def test_whichenv_debug(caplog: pytest.LogCaptureFixture, cd_tmp_path: Path) -> None:
    """Test ``runway whichenv`` debug."""
    caplog.set_level(logging.DEBUG, logger="runway")
    runway_yml = cd_tmp_path / "runway.yml"
    runway_yml.write_text(yaml.safe_dump({"deployments": [], "ignore_git_branch": True}))
    runner = CliRunner()
    result = runner.invoke(cli, ["whichenv", "--debug"])
    assert result.exit_code == 0
    assert "runway log level: 10" in caplog.messages
    assert "set dependency log level to debug" not in caplog.messages


def test_whichenv_debug_debug(caplog: pytest.LogCaptureFixture, cd_tmp_path: Path) -> None:
    """Test ``runway whichenv`` debug."""
    caplog.set_level(logging.DEBUG, logger="runway")
    runway_yml = cd_tmp_path / "runway.yml"
    runway_yml.write_text(yaml.safe_dump({"deployments": [], "ignore_git_branch": True}))
    runner = CliRunner()
    result = runner.invoke(cli, ["whichenv"], env={"DEBUG": "2"})
    assert result.exit_code == 0
    assert "runway log level: 10" in caplog.messages
    assert "set dependency log level to debug" in caplog.messages


def test_whichenv_invalid_debug_environ(cd_tmp_path: Path) -> None:
    """Test ``runway whichenv`` with invalid debug environ."""
    runway_yml = cd_tmp_path / "runway.yml"
    runway_yml.write_text(yaml.safe_dump({"deployments": [], "ignore_git_branch": True}))
    runner = CliRunner()
    result = runner.invoke(cli, ["whichenv"], env={"DEBUG": "invalid"})
    assert result.exit_code == 2
    assert "Invalid value for '--debug': 'invalid' is not a valid integer" in result.output
