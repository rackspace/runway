"""Test locked stack."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from runway._cli import cli

if TYPE_CHECKING:
    from collections.abc import Generator

    from click.testing import CliRunner, Result

CURRENT_DIR = Path(__file__).parent


@pytest.fixture(scope="module")
def deploy_result(cli_runner: CliRunner) -> Generator[Result, None, None]:
    """Execute `runway deploy` with `runway destroy` as a cleanup step."""
    yield cli_runner.invoke(cli, ["deploy"], env={"CI": "1"})
    assert cli_runner.invoke(cli, ["destroy"], env={"CI": "1"}).exit_code == 0
    shutil.rmtree(CURRENT_DIR / ".runway", ignore_errors=True)


@pytest.mark.order("first")
def test_deploy_exit_code(deploy_result: Result) -> None:
    """Test deploy exit code."""
    assert deploy_result.exit_code == 0


def test_deploy_log_messages(deploy_result: Result) -> None:
    """Test deploy log messages."""
    expected_lines = [
        "00-bootstrap.yaml:deploy (complete)",
        "01-locked-stack.yaml:deploy (in progress)",
        "locked-stack-vpc:skipped (locked)",
        "locked-stack-bastion:submitted (creating new stack)",
        "locked-stack-bastion:complete (creating new stack)",
        "01-locked-stack.yaml:deploy (complete)",
    ]
    expected = "\n".join(f"[runway] {msg}" for msg in expected_lines)
    assert expected in deploy_result.stdout, (
        "stdout does not match expected\n\nEXPECTED:\n"
        f"{expected}\n\nSTDOUT:\n{deploy_result.stdout}"
    )
