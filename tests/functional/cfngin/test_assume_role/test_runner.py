"""Test Runway assume role."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Generator

import boto3
import pytest
import yaml
from botocore.exceptions import ClientError

from runway._cli import cli

if TYPE_CHECKING:
    from click.testing import CliRunner, Result

AWS_REGION = "us-east-1"
CURRENT_DIR = Path(__file__).parent


def assert_session_belongs_to_account(session: boto3.Session, account_id: str) -> None:
    """Assert boto3.Session belongs to expected account."""
    assert session.client("sts").get_caller_identity()["Account"] == account_id


@pytest.fixture(scope="module")
def assumed_session(main_session: boto3.Session, variables: Dict[str, Any]) -> boto3.Session:
    """boto3 session for assumed account."""
    role_arn = variables["runner_role"]["test-alt"]
    sts_client = main_session.client("sts")

    creds = sts_client.assume_role(
        DurationSeconds=3600, RoleArn=role_arn, RoleSessionName=__name__
    )["Credentials"]
    return boto3.Session(
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
        region_name=AWS_REGION,
    )


@pytest.fixture(scope="module")
def main_session() -> boto3.Session:
    """boto3 session for main account."""
    return boto3.Session(region_name=AWS_REGION)


@pytest.fixture(scope="module")
def variables() -> Dict[str, Any]:
    """Contents of runway.variables.yml."""
    return yaml.safe_load((CURRENT_DIR / "runway.variables.yml").read_bytes())


@pytest.fixture(scope="module")
def deploy_result(cli_runner: CliRunner) -> Generator[Result, None, None]:
    """Execute `runway deploy` with `runway destroy` as a cleanup step."""
    yield cli_runner.invoke(cli, ["deploy", "--debug"], env={"CI": "1"})


@pytest.fixture(scope="module")
def destroy_result(cli_runner: CliRunner) -> Generator[Result, None, None]:
    """Execute `runway deploy` with `runway destroy` as a cleanup step."""
    yield cli_runner.invoke(cli, ["destroy"], env={"CI": "1"})
    shutil.rmtree(CURRENT_DIR / ".runway", ignore_errors=True)


@pytest.mark.order("first")
def test_deploy_exit_code(deploy_result: Result) -> None:
    """Test deploy exit code."""
    assert deploy_result.exit_code == 0


def test_does_not_exist_in_main_account(
    main_session: boto3.Session, namespace: str, variables: Dict[str, Any]
) -> None:
    """Test that the deployed stack does not exist in the main test account."""
    assert_session_belongs_to_account(main_session, variables["account_id"]["test"])
    with pytest.raises(ClientError) as excinfo:
        main_session.client("cloudformation").describe_stacks(
            StackName=f"{namespace}-test-assume-role"
        )
    assert "does not exist" in str(excinfo.value)


def test_exists_in_assumed_account(
    assumed_session: boto3.Session, namespace: str, variables: Dict[str, Any]
) -> None:
    """Test that the deployed stack exists in the assumed account."""
    assert_session_belongs_to_account(assumed_session, variables["account_id"]["test-alt"])
    assert assumed_session.client("cloudformation").describe_stacks(
        StackName=f"{namespace}-test-assume-role"
    )["Stacks"]


@pytest.mark.order("last")
def test_destroy_exit_code(destroy_result: Result) -> None:
    """Test destroy exit code."""
    assert destroy_result.exit_code == 0
