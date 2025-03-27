"""Pytest configuration, fixtures, and plugins."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest

from runway.config import CfnginConfig, RunwayConfig
from runway.context import CfnginContext, RunwayContext
from runway.core.components import DeployEnvironment
from runway.env_mgr.tfenv import TFEnvManager

from ..factories import cli_runner_factory

if TYPE_CHECKING:
    from collections.abc import Generator

    from click.testing import CliRunner


def pytest_ignore_collect(path: Any, config: pytest.Config) -> bool:  # noqa: ARG001
    """Determine if this directory should have its tests collected."""
    return not config.option.functional


@pytest.fixture(autouse=True, scope="module")
def cd_test_dir(request: pytest.FixtureRequest) -> Generator[Path, None, None]:
    """Change directory to test directory."""
    test_dir = request.path.parent
    original_wd = Path.cwd()
    try:
        os.chdir(test_dir)
        yield test_dir
    finally:
        os.chdir(original_wd)


@pytest.fixture(scope="module")
def cfngin_bucket() -> str:
    """Return name of CFNgin bucket used for tests."""
    return "runway-testing-lab-cfngin-bucket-us-east-1"


@pytest.fixture(scope="module")
def cfngin_bucket_alt() -> str:
    """Return name of CFNgin bucket used for tests in the alt account."""
    return "runway-testing-alt-lab-cfngin-bucket-us-east-1"


@pytest.fixture(scope="module")
def cfngin_config(
    request: pytest.FixtureRequest, runway_config: RunwayConfig, runway_context: RunwayContext
) -> CfnginConfig:
    """Find and return the CFNgin config."""
    runway_config.deployments[0].resolve(runway_context, variables=runway_config.variables)
    return CfnginConfig.parse_file(
        path=request.path.parent / "cfngin.yml",
        parameters=runway_config.deployments[0].parameters,
    )


@pytest.fixture(scope="module")
def cfngin_context(
    cd_test_dir: Path,
    cfngin_config: CfnginConfig,
    runway_config: RunwayConfig,
    runway_context: RunwayContext,
) -> CfnginContext:
    """Return CFNgin context."""
    return CfnginContext(
        config=cfngin_config,
        config_path=cd_test_dir / "cfngin.yml",
        deploy_environment=runway_context.env,
        parameters=runway_config.deployments[0].parameters,
    )


@pytest.fixture(scope="module")
def cli_runner(cd_test_dir: Path, request: pytest.FixtureRequest) -> CliRunner:  # noqa: ARG001
    """Initialize instance of `click.testing.CliRunner`."""
    return cli_runner_factory(request)


@pytest.fixture(scope="module")
def cli_runner_isolated(cli_runner: CliRunner) -> Generator[CliRunner, None, None]:
    """Initialize instance of `click.testing.CliRunner` with `isolate_filesystem()` called."""
    with cli_runner.isolated_filesystem():
        yield cli_runner


@pytest.fixture(scope="module")
def namespace() -> str:
    """Get CFNgin namespace."""
    return os.getenv("RUNWAY_TEST_NAMESPACE", f"{os.getenv('USER', 'user')}-local")


@pytest.fixture(scope="module", autouse=True)
def patch_tfenv_dir(tfenv_dir: Path) -> Generator[None, None, None]:
    """Patch TFEnvManager.env_dir."""
    mocker = patch.object(TFEnvManager, "env_dir", tfenv_dir)
    mocker.start()
    yield
    mocker.stop()


@pytest.fixture(scope="module")
def runway_config(cd_test_dir: Path) -> RunwayConfig:
    """Find and return the Runway config."""
    return RunwayConfig.parse_file(path=cd_test_dir)


@pytest.fixture(scope="module")
def runway_context(cd_test_dir: Path) -> RunwayContext:
    """Create Runway context."""
    return RunwayContext(
        deploy_environment=DeployEnvironment(explicit_name="test", root_dir=cd_test_dir)
    )
