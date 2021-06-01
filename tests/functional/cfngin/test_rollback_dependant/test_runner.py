"""Test failed stack with dependency."""
# pylint: disable=redefined-outer-name,unused-argument
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
    """Execute `runway deploy` with `runway destory` as a cleanup step."""
    yield cli_runner.invoke(cli, ["deploy"], env={"CI": "1"})
    assert cli_runner.invoke(cli, ["destroy"], env={"CI": "1"}).exit_code == 0
    shutil.rmtree(CURRENT_DIR / ".runway", ignore_errors=True)


@pytest.mark.order("first")
def test_deploy_exit_code(deploy_result: Result) -> None:
    """Test deploy exit code."""
    assert deploy_result.exit_code != 0


@pytest.mark.order(after="test_deploy_exit_code")
def test_deploy_log_messages(deploy_result: Result, namespace: str) -> None:
    """Test deploy log messages."""
    expected_lines = [
        "cfngin.yml:deploy (in progress)",
        "dependent-rollback-parent:submitted (creating new stack)",
        "dependent-rollback-parent:submitted (rolling back new stack)",
        f"{namespace}-dependent-rollback-parent:roll back reason: "
        "The following resource(s) failed to create: [BrokenWaitCondition]. "
        "Rollback requested by user.",
        "dependent-rollback-parent:failed (rolled back new stack)",
        "dependent-rollback-child:failed (dependency has failed)",
        "The following steps failed: dependent-rollback-parent, dependent-rollback-child",
    ]
    expected = "\n".join(f"[runway] {msg}" for msg in expected_lines)
    assert expected in deploy_result.stdout, (
        "stdout does not match expected\n\nEXPECTED:\n"
        f"{expected}\n\nSTDOUT:\n{deploy_result.stdout}"
    )
