"""Test duplicate stack names."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Generator

import pytest

from runway._cli import cli

if TYPE_CHECKING:
    from click.testing import CliRunner, Result

CURRENT_DIR = Path(__file__).parent


@pytest.fixture(scope="module")
def deploy_result(cli_runner: CliRunner) -> Generator[Result, None, None]:
    """Execute `runway deploy` with `runway destroy` as a cleanup step."""
    yield cli_runner.invoke(cli, ["deploy"], env={"CI": "1"})
    shutil.rmtree(CURRENT_DIR / ".runway", ignore_errors=True)


@pytest.mark.order("first")
def test_deploy_exit_code(deploy_result: Result) -> None:
    """Test deploy exit code."""
    assert deploy_result.exit_code != 0


@pytest.mark.order(after="test_deploy_exit_code")
def test_deploy_log_messages(deploy_result: Result) -> None:
    """Test deploy log messages."""
    expected_lines = [
        "[runway] 1 validation error for CfnginConfigDefinitionModel",
        "stacks",
        "  Duplicate stack vpc found at index 0 (type=value_error)",
    ]
    expected = "\n".join(expected_lines)
    assert expected in deploy_result.stdout, (
        "stdout does not match expected\n\nEXPECTED:\n"
        f"{expected}\n\nSTDOUT:\n{deploy_result.stdout}"
    )
