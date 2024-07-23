"""Test using raw CloudFormation template."""

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


@pytest.fixture(scope="module")
def deploy_no_change_result(cli_runner: CliRunner) -> Result:
    """Execute `runway deploy` with no cleanup step."""
    return cli_runner.invoke(cli, ["deploy"], env={"CI": "1"})


@pytest.fixture(scope="module")
def destroy_result(cli_runner: CliRunner) -> Result:
    """Execute `runway destroy`."""
    return cli_runner.invoke(cli, ["destroy"], env={"CI": "1"})


@pytest.mark.order("first")
def test_deploy_exit_code(deploy_result: Result) -> None:
    """Test deploy exit code."""
    assert deploy_result.exit_code == 0


@pytest.mark.order(after="test_deploy_exit_code")
def test_deploy_log_messages(deploy_result: Result) -> None:
    """Test deploy log messages."""
    expected_lines = [
        "deployment_1:processing deployment (in progress)",
        "deployment_1:processing regions sequentially...",
        "",
        "deployment_1.test_raw_cfn:processing module in us-east-1 (in progress)",
        "cfngin.yml:init (in progress)",
        "skipped; cfngin_bucket not defined",
        "cfngin.yml:init (complete)",
        "cfngin.yml:deploy (in progress)",
        "raw-template-vpc:submitted (creating new stack)",
        "raw-template-vpc:complete (creating new stack)",
        "cfngin.yml:deploy (complete)",
        "deployment_1.test_raw_cfn:processing module in us-east-1 (complete)",
        "deployment_1:processing deployment (complete)",
    ]
    expected = "\n".join(f"[runway] {msg}" for msg in expected_lines)
    assert expected in deploy_result.stdout, (
        "stdout does not match expected\n\nEXPECTED:\n"
        f"{expected}\n\nSTDOUT:\n{deploy_result.stdout}"
    )


@pytest.mark.order(after="test_deploy_log_messages")
def test_deploy_no_change_exit_code(deploy_no_change_result: Result) -> None:
    """Test deploy no change exit code."""
    assert deploy_no_change_result.exit_code == 0


@pytest.mark.order(after="test_deploy_no_change_exit_code")
def test_deploy_no_change_log_messages(deploy_no_change_result: Result) -> None:
    """Test deploy no change log messages."""
    expected_lines = [
        "deployment_1:processing deployment (in progress)",
        "deployment_1:processing regions sequentially...",
        "",
        "deployment_1.test_raw_cfn:processing module in us-east-1 (in progress)",
        "cfngin.yml:init (in progress)",
        "skipped; cfngin_bucket not defined",
        "cfngin.yml:init (complete)",
        "cfngin.yml:deploy (in progress)",
        "raw-template-vpc:skipped (nochange)",
        "cfngin.yml:deploy (complete)",
        "deployment_1.test_raw_cfn:processing module in us-east-1 (complete)",
        "deployment_1:processing deployment (complete)",
    ]
    expected = "\n".join(f"[runway] {msg}" for msg in expected_lines)
    assert expected in deploy_no_change_result.stdout, (
        "stdout does not match expected\n\nEXPECTED:\n"
        f"{expected}\n\nSTDOUT:\n{deploy_no_change_result.stdout}"
    )


@pytest.mark.order(after="test_deploy_no_change_log_messages")
def test_destroy_exit_code(destroy_result: Result) -> None:
    """Test destroy exit code."""
    assert destroy_result.exit_code == 0


@pytest.mark.order(after="test_destroy_exit_code")
def test_destroy_log_messages(destroy_result: Result) -> None:
    """Test destroy log messages."""
    expected_lines = [
        "deployment_1:processing deployment (in progress)",
        "deployment_1:processing regions sequentially...",
        "",
        "deployment_1.test_raw_cfn:processing module in us-east-1 (in progress)",
        "cfngin.yml:destroy (in progress)",
        "raw-template-vpc:submitted (submitted for destruction)",
        "raw-template-vpc:complete (stack destroyed)",
        "cfngin.yml:destroy (complete)",
        "deployment_1.test_raw_cfn:processing module in us-east-1 (complete)",
        "deployment_1:processing deployment (complete)",
    ]
    expected = "\n".join(f"[runway] {msg}" for msg in expected_lines)
    assert expected in destroy_result.stdout, (
        "stdout does not match expected\n\nEXPECTED:\n"
        f"{expected}\n\nSTDOUT:\n{destroy_result.stdout}"
    )
