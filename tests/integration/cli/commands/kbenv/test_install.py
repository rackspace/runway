"""Test ``runway kbenv install`` command."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from runway._cli import cli
from runway.env_mgr.kbenv import KB_VERSION_FILENAME

if TYPE_CHECKING:
    import pytest
    from click.testing import CliRunner


def test_kbenv_install(
    caplog: pytest.LogCaptureFixture, cli_runner: CliRunner, tmp_path: Path
) -> None:
    """Test ``runway kbenv install`` reading version from a file.

    For best results, remove any existing installs.

    """
    caplog.set_level(logging.DEBUG, logger="runway._cli.commands._kbenv")
    (tmp_path / KB_VERSION_FILENAME).write_text("v1.14.1")
    result = cli_runner.invoke(cli, ["kbenv", "install"])
    assert result.exit_code == 0

    kb_bin = Path(caplog.messages[-1].replace("kubectl path: ", ""))
    assert kb_bin.exists()


def test_kbenv_install_no_version_file(
    caplog: pytest.LogCaptureFixture, cli_runner: CliRunner
) -> None:
    """Test ``runway kbenv install`` no version file."""
    caplog.set_level(logging.WARNING, logger="runway")
    result = cli_runner.invoke(cli, ["kbenv", "install"])
    assert result.exit_code == 1

    assert (
        f"kubectl version not specified and {KB_VERSION_FILENAME} file not found"
        in caplog.messages[0]
    )


def test_kbenv_install_version(caplog: pytest.LogCaptureFixture, cli_runner: CliRunner) -> None:
    """Test ``runway kbenv install <version>``.

    For best results, remove any existing installs.

    """
    caplog.set_level(logging.DEBUG, logger="runway._cli.commands._kbenv")
    result = cli_runner.invoke(cli, ["kbenv", "install", "v1.14.0"])
    assert result.exit_code == 0

    kb_bin = Path(caplog.messages[-1].replace("kubectl path: ", ""))
    assert kb_bin.exists()
