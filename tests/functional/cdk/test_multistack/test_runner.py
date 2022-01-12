"""Test multiple stacks.

When making changes to the TypeScript source code of this test please ensure it
passes linting (not done automatically since this should rarely change).

To fix linting issue automatically, run the following from this directory::

    npm ci
    npm run lintfix

"""
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


@pytest.fixture(scope="module")
def destroy_result(cli_runner: CliRunner) -> Generator[Result, None, None]:
    """Execute `runway destroy`."""
    yield cli_runner.invoke(cli, ["destroy"], env={"CI": "1"})
    shutil.rmtree(CURRENT_DIR / "cdk.out", ignore_errors=True)
    shutil.rmtree(CURRENT_DIR / "node_modules", ignore_errors=True)
    shutil.rmtree(CURRENT_DIR / ".runway", ignore_errors=True)
    for f in CURRENT_DIR.glob("**/*.js"):
        f.unlink()
    for f in CURRENT_DIR.glob("**/*.d.ts"):
        f.unlink()


@pytest.mark.order("first")
def test_deploy_exit_code(deploy_result: Result) -> None:
    """Test deploy exit code."""
    assert deploy_result.exit_code == 0


def test_destroy_exit_code(destroy_result: Result) -> None:
    """Test destory exit code."""
    assert destroy_result.exit_code == 0
