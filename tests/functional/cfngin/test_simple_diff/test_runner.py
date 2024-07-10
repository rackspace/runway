"""Run a simple test of `runway plan` for CFNgin."""

from __future__ import annotations

from typing import TYPE_CHECKING, Generator

import pytest

from runway._cli import cli

if TYPE_CHECKING:
    from click.testing import CliRunner, Result

    from runway.config import RunwayConfig


@pytest.fixture(scope="module")
def initial_deploy(cli_runner: CliRunner) -> Generator[None, None, None]:
    """Execute `runway deploy` with `runway destroy` as a cleanup step."""
    assert cli_runner.invoke(cli, ["deploy"], env={"CI": "1"}).exit_code == 0
    yield
    assert cli_runner.invoke(cli, ["destroy"], env={"CI": "1"}).exit_code == 0


@pytest.fixture(scope="module")
def plan_result(cli_runner: CliRunner, initial_deploy: None) -> Result:
    """Execute `runway plan`."""
    return cli_runner.invoke(cli, ["plan"], env={"CI": "1", "DEPLOY_ENVIRONMENT": "test2"})


@pytest.mark.order("first")
def test_plan_exit_code(plan_result: Result) -> None:
    """Test plan exit code."""
    assert plan_result.exit_code == 0


@pytest.mark.order(after="test_plan_exit_code")
def test_plan_log_messages(plan_result: Result, runway_config: RunwayConfig) -> None:
    """Test plan exit code."""
    expected_lines = [
        "--- Old Parameters",
        "+++ New Parameters",
        "******************",
        f"-InstanceType = {runway_config.variables['instance_type']['test']}",
        f"+InstanceType = {runway_config.variables['instance_type']['test2']}",
        "",
        "- ResourceChange:",
        "    Action: Add",
        "    Details: []",
        "    LogicalResourceId: VPC1",
        "    ResourceType: AWS::CloudFormation::WaitConditionHandle",
        "    Scope: []",
        "  Type: Resource",
    ]
    expected = "\n".join(expected_lines)
    assert (
        expected in plan_result.stdout
    ), f"stdout does not match expected\n\nEXPECTED:\n{expected}\n\nSTDOUT:\n{plan_result.stdout}"
