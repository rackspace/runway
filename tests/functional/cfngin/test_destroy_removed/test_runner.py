"""Test destroy stack removed from persistent graph."""
# pylint: disable=redefined-outer-name
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


@pytest.fixture(scope="module")
def destroy_result(cli_runner: CliRunner) -> Result:
    """Execute `runway destroy`."""
    return cli_runner.invoke(cli, ["destroy"], env={"CI": "1"})


@pytest.mark.order("first")
def test_deploy_exit_code(deploy_result: Result) -> None:
    """Test deploy exit code."""
    assert deploy_result.exit_code == 0


def test_deploy_log_messages(deploy_result: Result, namespace: str) -> None:
    """Test deploy log messages.

    Unlike most other tests, these log messages can't be checked as a block
    as they could appear in variable order and contain a UUID.

    """
    assert (
        "00-bootstrap:persistant graph object does not exist in s3; creating one now..."
        in deploy_result.stdout
    )
    assert (
        '00-bootstrap:locked persistent graph "runway-testing-lab-cfngin-bucket-us-east-1'
        f'/persistent_graphs/{namespace}/test.json" with lock ID "'
        in deploy_result.stdout
    )
    assert (
        '00-bootstrap:unlocked persistent graph "runway-testing-lab-cfngin-bucket-us-east-1'
        f'/persistent_graphs/{namespace}/test.json"' in deploy_result.stdout
    )
    assert (
        '01-removed:locked persistent graph "runway-testing-lab-cfngin-bucket-us-east-1'
        f'/persistent_graphs/{namespace}/test.json" with lock ID "'
        in deploy_result.stdout
    )
    assert (
        f"{namespace}-other:removed from the CFNgin config file; it is being destroyed"
        in deploy_result.stdout
    )
    assert "other:submitted (submitted for destruction)" in deploy_result.stdout
    assert "vpc:skipped (nochange)" in deploy_result.stdout
    assert "bastion:skipped (nochange)" in deploy_result.stdout
    assert "other:complete (stack destroyed)" in deploy_result.stdout
    assert (
        '01-removed:unlocked persistent graph "runway-testing-lab-cfngin-bucket-us-east-1/'
        f'persistent_graphs/{namespace}/test.json"' in deploy_result.stdout
    )


@pytest.mark.order(after="test_deploy_log_messages")
def test_destroy_exit_code(destroy_result: Result) -> None:
    """Test destory exit code."""
    assert destroy_result.exit_code == 0


@pytest.mark.order(after="test_destroy_exit_code")
def test_destroy_log_messages(destroy_result: Result) -> None:
    """Test destroy log messages."""
    assert (
        "persistent graph deleted; does not need to be unlocked"
        in destroy_result.stdout
    )
