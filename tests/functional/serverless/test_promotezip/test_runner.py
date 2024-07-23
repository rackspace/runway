"""Test promote zip between environments."""

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
def deploy_promotezip_result(cli_runner: CliRunner) -> Result:
    """Execute `runway deploy` with `runway destroy` as a cleanup step."""
    return cli_runner.invoke(
        cli,
        ["deploy", "--tag", "sls"],
        env={"DEPLOY_ENVIRONMENT": "promotezip", "CI": "1"},
    )


@pytest.fixture(scope="module")
def deploy_result(cli_runner: CliRunner) -> Result:
    """Execute `runway deploy` with `runway destroy` as a cleanup step."""
    return cli_runner.invoke(cli, ["deploy"], env={"CI": "1"})


@pytest.fixture(scope="module")
def destroy_promotezip_result(cli_runner: CliRunner) -> Result:
    """Execute `runway destroy`."""
    return cli_runner.invoke(
        cli,
        ["destroy", "--tag", "sls"],
        env={"DEPLOY_ENVIRONMENT": "promotezip", "CI": "1"},
    )


@pytest.fixture(scope="module")
def destroy_result(cli_runner: CliRunner) -> Generator[Result, None, None]:
    """Execute `runway destroy`."""
    yield cli_runner.invoke(cli, ["destroy"], env={"CI": "1"})
    # cleanup files
    shutil.rmtree(CURRENT_DIR / ".runway", ignore_errors=True)
    shutil.rmtree(CURRENT_DIR / ".serverless", ignore_errors=True)
    shutil.rmtree(CURRENT_DIR / "bootstrap.cfn" / ".runway", ignore_errors=True)
    shutil.rmtree(CURRENT_DIR / "node_modules", ignore_errors=True)


@pytest.mark.order("first")
def test_deploy_exit_code(deploy_result: Result) -> None:
    """Test deploy exit code."""
    assert deploy_result.exit_code == 0


@pytest.mark.order(after="test_deploy_exit_code")
def test_deploy_promotezip_exit_code(deploy_promotezip_result: Result) -> None:
    """Test deploy exit code."""
    assert deploy_promotezip_result.exit_code == 0


@pytest.mark.order(after="test_deploy_promotezip_exit_code")
def test_deploy_promotezip_log_messages(deploy_promotezip_result: Result) -> None:
    """Test deploy log messages."""
    assert (
        "test_promotezip:found existing package for helloWorld0" in deploy_promotezip_result.stdout
    ), f"expected not in stdout:\n{deploy_promotezip_result.stdout}"
    assert (
        "downloading s3://" in deploy_promotezip_result.stdout
    ), f"expected not in stdout:\n{deploy_promotezip_result.stdout}"
    assert (
        "est_promotezip:found existing package for helloWorld1" in deploy_promotezip_result.stdout
    ), f"expected not in stdout:\n{deploy_promotezip_result.stdout}"


@pytest.mark.order(after="test_deploy_promotezip_log_messages")
def test_destroy_promotezip_exit_code(destroy_promotezip_result: Result) -> None:
    """Test destroy exit code."""
    assert destroy_promotezip_result.exit_code == 0


@pytest.mark.order("last")
def test_destroy_exit_code(destroy_result: Result) -> None:
    """Test destroy exit code."""
    assert destroy_result.exit_code == 0
