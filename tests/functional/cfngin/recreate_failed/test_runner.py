"""Test recreation of a failed deployment."""
# pylint: disable=redefined-outer-name,unused-argument
from __future__ import annotations

from typing import TYPE_CHECKING, Generator

import pytest

from runway._cli import cli

if TYPE_CHECKING:
    from click.testing import CliRunner, Result


@pytest.fixture(scope="module")
def deploy_bad_result(cli_runner: CliRunner) -> Generator[Result, None, None]:
    """Execute `runway deploy` with `runway destory` as a cleanup step."""
    yield cli_runner.invoke(cli, ["deploy", "--tag", "bad"], env={"CI": "1"})
    assert (
        cli_runner.invoke(cli, ["destroy", "--tag", "good"], env={"CI": "1"}).exit_code
        == 0
    )


@pytest.fixture(scope="module")
def deploy_good_result(cli_runner: CliRunner) -> Result:
    """Execute `runway deploy` with `runway destory` as a cleanup step."""
    return cli_runner.invoke(cli, ["deploy", "--tag", "good"], env={"CI": "1"})


@pytest.mark.order("first")
def test_deploy_bad_exit_code(deploy_bad_result: Result) -> None:
    """Test deploy bad exit code."""
    assert deploy_bad_result.exit_code != 0


@pytest.mark.order(after="test_deploy_bad_exit_code")
def test_deploy_bad_log_messages(deploy_bad_result: Result, namespace: str) -> None:
    """Test deploy bad log messages."""
    expected_lines = [
        "cfngin.yml:deploy (in progress)",
        "recreate-failed:submitted (creating new stack)",
        "recreate-failed:submitted (rolling back new stack)",
        f"{namespace}-recreate-failed:roll back reason: "
        "The following resource(s) failed to create: [BrokenWaitCondition]. "
        "Rollback requested by user.",
        "recreate-failed:failed (rolled back new stack)",
        "The following steps failed: recreate-failed",
    ]
    expected = "\n".join(f"[runway] {msg}" for msg in expected_lines)
    assert expected in deploy_bad_result.stdout, (
        "stdout does not match expected\n\nEXPECTED:\n"
        f"{expected}\n\nSTDOUT:\n{deploy_bad_result.stdout}"
    )


@pytest.mark.order(after="test_deploy_bad_log_messages")
def test_deploy_good_exit_code(deploy_good_result: Result) -> None:
    """Test deploy good exit code."""
    assert deploy_good_result.exit_code == 0


@pytest.mark.order(after="test_deploy_good_exit_code")
def test_deploy_good_log_messages(deploy_good_result: Result, namespace: str) -> None:
    """Test deploy good log messages."""
    expected_lines = [
        "cfngin.yml:deploy (in progress)",
        f"{namespace}-recreate-failed:destroying stack for re-creation",
        "recreate-failed:submitted (destroying stack for re-creation)",
        "recreate-failed:submitted (creating new stack)",
        "recreate-failed:complete (creating new stack)",
    ]
    expected = "\n".join(f"[runway] {msg}" for msg in expected_lines)
    assert expected in deploy_good_result.stdout, (
        "stdout does not match expected\n\nEXPECTED:\n"
        f"{expected}\n\nSTDOUT:\n{deploy_good_result.stdout}"
    )
