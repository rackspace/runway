"""Test parallel deployment."""
# pylint: disable=redefined-outer-name
from __future__ import annotations

import platform
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


@pytest.fixture(scope="module")
def destroy_result(cli_runner: CliRunner) -> Generator[Result, None, None]:
    """Execute `runway destroy`."""
    yield cli_runner.invoke(cli, ["destroy"], env={"CI": "1"})
    shutil.rmtree(CURRENT_DIR / ".runway", ignore_errors=True)
    shutil.rmtree(CURRENT_DIR / "child-01.cfn" / ".runway", ignore_errors=True)
    shutil.rmtree(CURRENT_DIR / "child-02.cfn" / ".runway", ignore_errors=True)


@pytest.mark.order("first")
@pytest.mark.skipif(
    platform.system() != "Linux", reason="only runs consistently on Linux"
)
def test_deploy_exit_code(deploy_result: Result) -> None:
    """Test deploy exit code."""
    assert deploy_result.exit_code == 0


@pytest.mark.order(after="test_deploy_exit_code")
@pytest.mark.skipif(
    platform.system() != "Linux", reason="only runs consistently on Linux"
)
def test_deploy_log_messages(deploy_result: Result) -> None:
    """Test deploy log messages."""
    assert (
        "deployment_1:processing regions in parallel... (output will be interwoven)"
        in deploy_result.stdout
    ), f"expected not in stdout:\n{deploy_result.stdout}"


@pytest.mark.order("last")
@pytest.mark.skipif(
    platform.system() != "Linux", reason="only runs consistently on Linux"
)
def test_destroy_exit_code(destroy_result: Result) -> None:
    """Test destroy exit code."""
    assert destroy_result.exit_code == 0
