"""Test ``runway run-stacker``."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from click.testing import CliRunner

from runway._cli import cli

if TYPE_CHECKING:
    from pathlib import Path

    from _pytest.logging import LogCaptureFixture

STACKER_CONFIG = """
namespace: test
stacks:
  test-stack:
    template_path: templates/test.yml
"""


def test_run_stacker_graph(cd_tmp_path: Path) -> None:
    """Test ``runway run-stacker graph``."""
    stacks_yml = cd_tmp_path / "stacks.yml"
    stacks_yml.write_text(STACKER_CONFIG)
    runner = CliRunner()
    result = runner.invoke(cli, ["run-stacker", "graph", stacks_yml.name])
    assert result.exit_code == 0
    assert "digraph digraph {" in result.output


def test_run_stacker_separator() -> None:
    """Test ``runway run-stacker -- --help``."""
    runner = CliRunner()
    result = runner.invoke(cli, ["run-stacker", "--", "--help"])
    assert result.exit_code == 0
    assert "usage: stacker" in result.output
    assert "runway" not in result.output


def test_run_stacker_version(caplog: LogCaptureFixture) -> None:
    """Test ``runway run-stacker --version``."""
    caplog.set_level(logging.WARNING, logger="runway.cli.commands")
    runner = CliRunner()
    result = runner.invoke(cli, ["run-stacker", "--version"])
    assert result.exit_code == 0
    assert "0.0.0" in result.output  # version is static
    assert caplog.messages == [
        "This command as been deprecated and will be removed in "
        "the next major release."
    ]
