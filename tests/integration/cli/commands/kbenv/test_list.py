"""Test ``runway kbenv list`` command."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from click.testing import CliRunner

from runway._cli import cli
from runway.env_mgr.kbenv import KBEnvManager

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import LogCaptureFixture
    from pytest_mock import MockerFixture


def test_kbenv_list(caplog: LogCaptureFixture, mocker: MockerFixture, tmp_path: Path) -> None:
    """Test ``runway kbenv list``."""
    caplog.set_level(logging.INFO, logger="runway.cli.commands.kbenv")
    mocker.patch.object(KBEnvManager, "versions_dir", tmp_path)
    version_dirs = [tmp_path / "v1.14.0", tmp_path / "v1.21.0"]
    for v_dir in version_dirs:
        v_dir.mkdir()
    (tmp_path / "something.txt").touch()
    runner = CliRunner()
    result = runner.invoke(cli, ["kbenv", "list"])
    assert result.exit_code == 0
    assert caplog.messages == ["kubectl versions installed:"]
    assert result.stdout == "\n".join(
        ["[runway] kubectl versions installed:", "v1.14.0", "v1.21.0", ""]
    )


def test_kbenv_list_none(caplog: LogCaptureFixture, mocker: MockerFixture, tmp_path: Path) -> None:
    """Test ``runway kbenv list`` no versions installed."""
    caplog.set_level(logging.WARNING, logger="runway.cli.commands.kbenv")
    mocker.patch.object(KBEnvManager, "versions_dir", tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["kbenv", "list"])
    assert result.exit_code == 0
    assert caplog.messages == [f"no versions of kubectl installed at path {tmp_path}"]
