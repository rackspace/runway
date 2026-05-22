"""Test ``runway variables``.

The below tests only cover the CLI.
Runway's core logic has been mocked out to test on separately from the CLI.

"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from click.testing import CliRunner

from runway._cli import cli

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

    from ...conftest import CpConfigTypeDef

MODULE = "runway._cli.commands._variables"


def test_variables(
    cd_tmp_path: Path,
    cp_config: CpConfigTypeDef,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test variables command basic execution."""
    caplog.set_level(logging.INFO, logger="runway")
    cp_config("simple_env_vars", cd_tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["variables"])
    assert result.exit_code == 0
    # Output should be YAML by default
    assert "deployments:" in result.output or "runway_variables:" in result.output


def test_variables_format_json(
    cd_tmp_path: Path,
    cp_config: CpConfigTypeDef,
) -> None:
    """Test variables command with JSON output format."""
    cp_config("simple_env_vars", cd_tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["variables", "--format", "json"])
    assert result.exit_code == 0
    # Should be valid JSON
    output = json.loads(result.output)
    assert "runway_variables" in output
    assert "deployments" in output


def test_variables_format_table(
    cd_tmp_path: Path,
    cp_config: CpConfigTypeDef,
) -> None:
    """Test variables command with table output format."""
    cp_config("simple_env_vars", cd_tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["variables", "--format", "table"])
    assert result.exit_code == 0
    # Table format should include headers
    assert "=== Runway Variables ===" in result.output
    assert "=== Deployment:" in result.output


def test_variables_with_env_vars(
    cd_tmp_path: Path,
    cp_config: CpConfigTypeDef,
) -> None:
    """Test variables command shows environment variables."""
    cp_config("simple_env_vars", cd_tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["variables", "--format", "json"])
    assert result.exit_code == 0
    output = json.loads(result.output)
    # Check that deployments have env_vars
    assert len(output["deployments"]) == 2
    # deployment_1 should have TEST_VAR_01
    deployment_1 = output["deployments"][0]
    assert deployment_1["name"] == "deployment_1"


def test_variables_options_deploy_environment(
    cd_tmp_path: Path, cp_config: CpConfigTypeDef
) -> None:
    """Test variables option -e, --deploy-environment."""
    cp_config("min_required", cd_tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["variables", "-e", "prod"])
    assert result.exit_code == 0

    result = runner.invoke(cli, ["variables", "--deploy-environment", "staging"])
    assert result.exit_code == 0


def test_variables_options_tag(
    caplog: pytest.LogCaptureFixture,
    cd_tmp_path: Path,
    cp_config: CpConfigTypeDef,
) -> None:
    """Test variables option --tag."""
    caplog.set_level(logging.ERROR, logger="runway.cli.commands.variables")
    cp_config("tagged_modules", cd_tmp_path)
    runner = CliRunner()

    # Single tag filter
    result = runner.invoke(cli, ["variables", "--tag", "app:test-app", "--format", "json"])
    assert result.exit_code == 0
    output = json.loads(result.output)
    # Should have filtered modules
    assert len(output["deployments"]) > 0

    # No match error
    result = runner.invoke(cli, ["variables", "--tag", "no-match"])
    assert result.exit_code == 1


def test_variables_options_module(
    caplog: pytest.LogCaptureFixture,
    cd_tmp_path: Path,
    cp_config: CpConfigTypeDef,
) -> None:
    """Test variables option --module."""
    caplog.set_level(logging.ERROR, logger="runway.cli.utils")
    cp_config("tagged_modules", cd_tmp_path)
    runner = CliRunner()

    # Exact module name match
    result = runner.invoke(cli, ["variables", "--module", "sampleapp-01.cfn", "--format", "json"])
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert len(output["deployments"]) == 1
    deployment = output["deployments"][0]
    # Should have modules filtered
    assert len(deployment["modules"]) >= 1

    # No match error
    result = runner.invoke(cli, ["variables", "--module", "nonexistent-module"])
    assert result.exit_code == 1


def test_variables_no_config(
    cd_tmp_path: Path,  # noqa: ARG001
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test variables command when no config file exists."""
    caplog.set_level(logging.ERROR, logger="runway")
    runner = CliRunner()
    result = runner.invoke(cli, ["variables"])
    assert result.exit_code == 1


def test_variables_with_parameters(
    cd_tmp_path: Path,
    cp_config: CpConfigTypeDef,
) -> None:
    """Test variables command shows parameters."""
    cp_config("variables_test", cd_tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["variables", "--format", "json"])
    assert result.exit_code == 0
    output = json.loads(result.output)
    deployment = output["deployments"][0]
    assert deployment["name"] == "test_deployment"
    # Verify parameters are shown
    assert "parameters" in deployment
