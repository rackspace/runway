"""Test ``runway kbenv list`` command."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from runway._cli import cli

if TYPE_CHECKING:
    from pathlib import Path

    import pytest
    from click.testing import CliRunner


def test_kbenv_list(
    caplog: pytest.LogCaptureFixture, cli_runner: CliRunner, versions_dir: Path
) -> None:
    """Test ``runway kbenv list``."""
    caplog.set_level(logging.INFO, logger="runway._cli.commands._kbenv")
    version_dirs = [versions_dir / "v1.14.0", versions_dir / "v1.21.0"]
    for v_dir in version_dirs:
        v_dir.mkdir()
    (versions_dir / "something.txt").touch()
    result = cli_runner.invoke(cli, ["kbenv", "list"])
    assert result.exit_code == 0
    assert caplog.messages == ["kubectl versions installed:"]
    assert {i.strip() for i in result.output.split("\n")} == {
        "[runway] kubectl versions installed:",
        "v1.14.0",
        "v1.21.0",
        "",
    }


def test_kbenv_list_none(
    caplog: pytest.LogCaptureFixture, cli_runner: CliRunner, versions_dir: Path
) -> None:
    """Test ``runway kbenv list`` no versions installed."""
    caplog.set_level(logging.WARNING, logger="runway._cli.commands._kbenv")
    result = cli_runner.invoke(cli, ["kbenv", "list"])
    assert result.exit_code == 0
    assert caplog.messages == [f"no versions of kubectl installed at path {versions_dir}"]
