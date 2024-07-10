"""Test ``runway tfenv list`` command."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from click.testing import CliRunner

from runway._cli import cli
from runway.env_mgr.tfenv import TFEnvManager

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import LogCaptureFixture
    from pytest_mock import MockerFixture


def test_tfenv_list(caplog: LogCaptureFixture, mocker: MockerFixture, tmp_path: Path) -> None:
    """Test ``runway tfenv list``."""
    caplog.set_level(logging.INFO, logger="runway.cli.commands.tfenv")
    mocker.patch.object(TFEnvManager, "versions_dir", tmp_path)
    version_dirs = [tmp_path / "0.13.0", tmp_path / "1.0.0"]
    for v_dir in version_dirs:
        v_dir.mkdir()
    (tmp_path / "something.txt").touch()
    runner = CliRunner()
    result = runner.invoke(cli, ["tfenv", "list"])
    assert result.exit_code == 0
    assert caplog.messages == ["Terraform versions installed:"]
    assert result.stdout == "\n".join(
        ["[runway] Terraform versions installed:", "0.13.0", "1.0.0", ""]
    )


def test_tfenv_list_none(caplog: LogCaptureFixture, mocker: MockerFixture, tmp_path: Path) -> None:
    """Test ``runway tfenv list`` no versions installed."""
    caplog.set_level(logging.WARNING, logger="runway.cli.commands.tfenv")
    mocker.patch.object(TFEnvManager, "versions_dir", tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["tfenv", "list"])
    assert result.exit_code == 0
    assert caplog.messages == [f"no versions of Terraform installed at path {tmp_path}"]
