"""Test migrating local backend to s3."""

from __future__ import annotations

import locale
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest

from runway._cli import cli
from runway.env_mgr.tfenv import TF_VERSION_FILENAME

if TYPE_CHECKING:
    from collections.abc import Iterator

    from _pytest.fixtures import SubRequest
    from click.testing import CliRunner, Result

CURRENT_DIR = Path(__file__).parent


@pytest.fixture(autouse=True, scope="module")
def tf_state_bucket(cli_runner: CliRunner) -> Iterator[None]:
    """Create Terraform state bucket and table."""
    cli_runner.invoke(cli, ["deploy", "--tag", "bootstrap"], env={"CI": "1"})
    yield
    destroy_result = cli_runner.invoke(cli, ["destroy", "--tag", "cleanup"], env={"CI": "1"})
    assert destroy_result.exit_code == 0


@pytest.fixture(
    autouse=True,
    params=["0.13.7", "0.14.11", "0.15.5", "1.4.6"],
    scope="module",
)
def tf_version(request: SubRequest) -> Iterator[str]:
    """Set Terraform version."""
    file_path = CURRENT_DIR / TF_VERSION_FILENAME
    file_path.write_text(
        cast(str, request.param) + "\n",
        encoding=locale.getpreferredencoding(do_setlocale=False),
    )
    yield cast(str, request.param)
    file_path.unlink(missing_ok=True)


@pytest.fixture
def deploy_local_backend_result(
    cli_runner: CliRunner,
    local_backend: Path,  # noqa: ARG001
) -> Result:
    """Execute `runway deploy` with `runway destroy` as a cleanup step."""
    return cli_runner.invoke(cli, ["deploy", "--tag", "local"], env={"CI": "1"})


@pytest.fixture
def deploy_s3_backend_result(
    cli_runner: CliRunner,
    s3_backend: Path,  # noqa: ARG001
) -> Iterator[Result]:
    """Execute `runway deploy` with `runway destroy` as a cleanup step."""
    yield cli_runner.invoke(cli, ["deploy", "--tag", "test"], env={"CI": "1"})
    # cleanup files
    shutil.rmtree(CURRENT_DIR / ".runway", ignore_errors=True)
    shutil.rmtree(CURRENT_DIR / ".terraform", ignore_errors=True)
    shutil.rmtree(CURRENT_DIR / "terraform.tfstate.d", ignore_errors=True)
    (CURRENT_DIR / "local_backend").unlink(missing_ok=True)
    (CURRENT_DIR / ".terraform.lock.hcl").unlink(missing_ok=True)


def test_deploy_local_backend_result(deploy_local_backend_result: Result) -> None:
    """Test deploy local backend result."""
    assert deploy_local_backend_result.exit_code == 0


def test_deploy_s3_backend_result(deploy_s3_backend_result: Result) -> None:
    """Test deploy s3 backend result."""
    # currently, this is expected to fail - Terraform prompts for user confirmation
    assert deploy_s3_backend_result.exit_code != 0
