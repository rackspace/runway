"""Test base functionality of Terraform being used through Runway.

This only aims to test basic functionality.
Other tests should exist to test low-level interactions with Terraform.

"""

from __future__ import annotations

import locale
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest

from runway._cli import cli
from runway.env_mgr.tfenv import TF_VERSION_FILENAME

if TYPE_CHECKING:
    from collections.abc import Generator

    from _pytest.fixtures import SubRequest
    from click.testing import CliRunner, Result

CURRENT_DIR = Path(__file__).parent


@pytest.fixture(
    autouse=True,
    params=["0.13.7", "0.14.11", "0.15.5", "1.4.6"],
    scope="module",
)
def tf_version(request: SubRequest) -> Generator[str, None, None]:
    """Set Terraform version."""
    file_path = CURRENT_DIR / TF_VERSION_FILENAME
    file_path.write_text(
        cast(str, request.param) + "\n",
        encoding=locale.getpreferredencoding(do_setlocale=False),
    )
    yield cast(str, request.param)
    file_path.unlink(missing_ok=True)


@pytest.fixture
def deploy_result(
    cli_runner: CliRunner,
    no_backend: Path,  # noqa: ARG001
) -> Generator[Result, None, None]:
    """Execute `runway deploy` with `runway destroy` as a cleanup step."""
    yield cli_runner.invoke(cli, ["deploy"], env={"CI": "1"})
    destroy_result = cli_runner.invoke(cli, ["destroy"], env={"CI": "1"})
    # cleanup files
    shutil.rmtree(CURRENT_DIR / ".runway", ignore_errors=True)
    shutil.rmtree(CURRENT_DIR / ".terraform", ignore_errors=True)
    shutil.rmtree(CURRENT_DIR / "terraform.tfstate.d", ignore_errors=True)
    (CURRENT_DIR / ".terraform.lock.hcl").unlink(missing_ok=True)
    assert destroy_result.exit_code == 0


def test_deploy_result(deploy_result: Result, tfenv_dir: Path, tf_version: str) -> None:
    """Test deploy result."""
    assert deploy_result.exit_code == 0
    expected_lines = [
        "test_base:unable to determine backend for module; no special handling will be applied",
        "test_base:init (in progress)",
        "backend file not found -- looking for one of: backend-test-us-east-1.hcl, "
        "backend-test-us-east-1.tfvars, backend-test.hcl, backend-test.tfvars, "
        "backend-us-east-1.hcl, backend-us-east-1.tfvars, backend.hcl, backend.tfvars",
    ]
    expected = "\n".join(f"[runway] {msg}" for msg in expected_lines)
    assert expected in deploy_result.stdout, (
        "stdout does not match expected\n\nEXPECTED:\n"
        f"{expected}\n\nSTDOUT:\n{deploy_result.stdout}"
    )
    # ensure selected tf version was installed and is being used
    # Runway does log this but, it can be unreliable due to how tests are ordered
    assert (tfenv_dir / "versions" / tf_version).is_dir()
