"""Test AWS Lambda hook."""
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
    """Execute `runway deploy` with `runway destroy` as a cleanup step."""
    yield cli_runner.invoke(cli, ["deploy"], env={"CI": "1"})
    assert cli_runner.invoke(cli, ["destroy"], env={"CI": "1"}).exit_code == 0
    shutil.rmtree(CURRENT_DIR / ".runway", ignore_errors=True)


@pytest.mark.order("first")
def test_deploy_exit_code(deploy_result: Result) -> None:
    """Test deploy exit code."""
    assert deploy_result.exit_code == 0


def test_deploy_log_messages_docker(deploy_result: Result) -> None:
    """Test deploy log messages."""
    assert (
        'using docker image "lambci/lambda:build-python3.9" to build deployment package...'
        in deploy_result.stdout
    )


def test_deploy_log_messages_invoke(deploy_result: Result, namespace: str) -> None:
    """Test deploy log messages."""
    assert f"{namespace}-dockerizepip returned 200" in deploy_result.stdout
    assert f"{namespace}-nondockerizepip returned 200" in deploy_result.stdout


def test_deploy_log_messages_pipenv(deploy_result: Result) -> None:
    """Test deploy log messages."""
    expected_lines = [
        "explicitly using pipenv",
        "creating requirements.txt from Pipfile...",
    ]
    expected = "\n".join(f"[runway] {msg}" for msg in expected_lines)
    assert expected in deploy_result.stdout, (
        "stdout does not match expected\n\nEXPECTED:\n"
        f"{expected}\n\nSTDOUT:\n{deploy_result.stdout}"
    )


def test_deploy_log_messages_upload(deploy_result: Result, namespace: str) -> None:
    """Test deploy log messages."""
    assert (
        f"uploading object: lambda_functions/{namespace}/lambda-dockerize-"
        in deploy_result.stdout
    )
    assert (
        f"uploading object: lambda_functions/{namespace}/lambda-nondockerize-"
        in deploy_result.stdout
    )
