"""Test ``runway tfenv run`` command."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from runway._cli import cli

if TYPE_CHECKING:
    from pathlib import Path

    import pytest
    from click.testing import CliRunner


def test_tfenv_run_no_version_file(cli_runner: CliRunner, caplog: pytest.LogCaptureFixture) -> None:
    """Test ``runway tfenv run -- --help`` no version file."""
    caplog.set_level(logging.ERROR, logger="runway")
    assert cli_runner.invoke(cli, ["tfenv", "run", "--", "--help"]).exit_code == 1
    assert "unable to find a .terraform-version file" in "\n".join(caplog.messages)


def test_tfenv_run_separator(
    cli_runner: CliRunner, capfd: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Test ``runway tfenv run -- --help``.

    Parsing of command using ``--`` as a separator between options and args.
    Everything that comes after the separator should be forwarded on as an arg
    and not parsed as an option by click. This is only required when trying to
    pass options shared with Runway such as ``--help``.

    """
    (tmp_path / ".terraform-version").write_text("0.12.0")
    result = cli_runner.invoke(cli, ["tfenv", "run", "--", "--help"])
    captured = capfd.readouterr()  # capfd required for subprocess
    assert result.exit_code == 0
    assert "runway" not in captured.out
    assert "terraform [-version] [-help] <command> [args]" in captured.out


def test_tfenv_run_version(
    cli_runner: CliRunner, capfd: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Test ``runway tfenv run --version``.

    Parsing of bare command.

    """
    version = "0.12.0"
    (tmp_path / ".terraform-version").write_text(version)
    result = cli_runner.invoke(cli, ["tfenv", "run", "--version"])
    captured = capfd.readouterr()  # capfd required for subprocess
    assert result.exit_code == 0
    assert f"Terraform v{version}" in captured.out
