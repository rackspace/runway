"""Test ``runway tfenv run`` command."""

# pylint: disable=unused-argument
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from click.testing import CliRunner

from runway._cli import cli

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import CaptureFixture, LogCaptureFixture


def test_tfenv_run_no_version_file(
    cd_tmp_path: Path, caplog: LogCaptureFixture
) -> None:
    """Test ``runway tfenv run -- --help`` no version file."""
    caplog.set_level(logging.ERROR, logger="runway")
    runner = CliRunner()
    result = runner.invoke(cli, ["tfenv", "run", "--", "--help"])
    assert result.exit_code == 1
    assert "unable to find a .terraform-version file" in "\n".join(caplog.messages)


def test_tfenv_run_separator(cd_tmp_path: Path, capfd: CaptureFixture[str]) -> None:
    """Test ``runway tfenv run -- --help``.

    Parsing of command using ``--`` as a separator between options and args.
    Everything that comes after the separator should be forwarded on as an arg
    and not parsed as an option by click. This is only required when trying to
    pass options shared with Runway such as ``--help``.

    """
    (cd_tmp_path / ".terraform-version").write_text("0.12.0")
    runner = CliRunner()
    result = runner.invoke(cli, ["tfenv", "run", "--", "--help"])
    captured = capfd.readouterr()  # capfd required for subprocess
    assert result.exit_code == 0
    assert "runway" not in captured.out
    assert "terraform [-version] [-help] <command> [args]" in captured.out


def test_tfenv_run_version(cd_tmp_path: Path, capfd: CaptureFixture[str]) -> None:
    """Test ``runway tfenv run --version``.

    Parsing of bare command.

    """
    version = "0.12.0"
    (cd_tmp_path / ".terraform-version").write_text(version)
    runner = CliRunner()
    result = runner.invoke(cli, ["tfenv", "run", "--version"])
    captured = capfd.readouterr()  # capfd required for subprocess
    assert result.exit_code == 0
    assert f"Terraform v{version}" in captured.out
