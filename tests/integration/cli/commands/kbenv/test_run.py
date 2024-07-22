"""Test ``runway kbenv run`` command."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from runway._cli import cli
from runway.env_mgr.kbenv import KB_VERSION_FILENAME

if TYPE_CHECKING:
    from pathlib import Path

    import pytest
    from click.testing import CliRunner


def test_kbenv_run_no_version_file(
    caplog: pytest.LogCaptureFixture,
    cli_runner: CliRunner,
) -> None:
    """Test ``runway kbenv run -- --help`` no version file."""
    caplog.set_level(logging.WARNING, logger="runway")
    result = cli_runner.invoke(cli, ["kbenv", "run", "--", "--help"])
    assert result.exit_code == 1

    assert (
        f"kubectl version not specified and {KB_VERSION_FILENAME} file not found"
        in caplog.messages[0]
    )


def test_kbenv_run_separator(
    capfd: pytest.CaptureFixture[str], cli_runner: CliRunner, tmp_path: Path
) -> None:
    """Test ``runway kbenv run -- --help``.

    Parsing of command using ``--`` as a separator between options and args.
    Everything that comes after the separator should be forwarded on as an arg
    and not parsed as an option by click. This is only required when trying to
    pass options shared with Runway such as ``--help``.

    """
    (tmp_path / KB_VERSION_FILENAME).write_text("v1.14.0")
    result = cli_runner.invoke(cli, ["kbenv", "run", "--", "--help"])
    captured = capfd.readouterr()  # capfd required for subprocess
    assert result.exit_code == 0
    assert "runway" not in captured.out
    assert "kubectl <command> --help" in captured.out


def test_kbenv_run_version(
    capfd: pytest.CaptureFixture[str], cli_runner: CliRunner, tmp_path: Path
) -> None:
    """Test ``runway kbenv run version``.

    Parsing of bare command.

    """
    (tmp_path / KB_VERSION_FILENAME).write_text("v1.14.0")
    result = cli_runner.invoke(cli, ["kbenv", "run", "version", "--client"])
    captured = capfd.readouterr()  # capfd required for subprocess
    assert result.exit_code == 0
    assert "v1.14.0" in captured.out
