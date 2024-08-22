"""Test ``runway new`` command."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import yaml
from click.testing import CliRunner

from runway._cli import cli

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_new(cd_tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test ``runway new`` command."""
    caplog.set_level(logging.INFO, logger="runway.cli")
    runner = CliRunner()
    result = runner.invoke(cli, ["new"])
    assert result.exit_code == 0

    # ensure the generated file is valid yaml
    runway_yml = yaml.safe_load((cd_tmp_path / "runway.yml").read_text())

    # simple check of the value
    assert len(runway_yml["deployments"][0]["modules"]) == 2

    assert caplog.messages == [
        "runway.yml generated",
        "See addition getting started information at "
        "https://runway.readthedocs.io/page/getting_started.html",
    ]


def test_new_file_exists(cd_tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test ``runway new`` command with existing file."""
    caplog.set_level(logging.ERROR, logger="runway.cli")
    (cd_tmp_path / "runway.yml").touch()
    runner = CliRunner()
    result = runner.invoke(cli, ["new"])
    assert result.exit_code == 1
    assert caplog.messages == ["There is already a runway.yml file in the current directory"]
