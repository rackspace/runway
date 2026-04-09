"""Test ``runway deploy``.

The below tests only cover the CLI.
Runway's core logic has been mocked out to test on separately from the CLI.

"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING
from unittest.mock import Mock

from click.testing import CliRunner

from runway._cli import cli
from runway._cli.changeset_executor import ChangesetExecutionError
from runway.config import RunwayConfig
from runway.context import RunwayContext
from runway.core import Runway

if TYPE_CHECKING:
    from pathlib import Path

    import pytest
    from pytest_mock import MockerFixture

    from ...conftest import CpConfigTypeDef

MODULE = "runway._cli.commands._deploy"


def test_deploy(
    cd_tmp_path: Path,
    cp_config: CpConfigTypeDef,
    caplog: pytest.LogCaptureFixture,
    mocker: MockerFixture,
) -> None:
    """Test deploy."""
    mock_runway = mocker.patch(f"{MODULE}.Runway", Mock(spec=Runway, spec_set=True))
    caplog.set_level(logging.INFO, logger="runway")
    cp_config("min_required", cd_tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["deploy"])
    assert result.exit_code == 0

    mock_runway.assert_called_once()
    assert isinstance(mock_runway.call_args.args[0], RunwayConfig)
    assert isinstance(mock_runway.call_args.args[1], RunwayContext)

    inst = mock_runway.return_value
    inst.deploy.assert_called_once()
    assert len(inst.deploy.call_args.args[0]) == 1


def test_deploy_options_ci(
    cd_tmp_path: Path, cp_config: CpConfigTypeDef, mocker: MockerFixture
) -> None:
    """Test deploy option --ci."""
    mock_runway = mocker.patch(f"{MODULE}.Runway", Mock(spec=Runway, spec_set=True))
    cp_config("min_required", cd_tmp_path)
    runner = CliRunner()
    assert runner.invoke(cli, ["deploy", "--ci"]).exit_code == 0
    assert mock_runway.call_args.args[1].env.ci is True

    assert runner.invoke(cli, ["deploy"]).exit_code == 0
    assert mock_runway.call_args.args[1].env.ci is False


def test_deploy_options_deploy_environment(
    cd_tmp_path: Path, cp_config: CpConfigTypeDef, mocker: MockerFixture
) -> None:
    """Test deploy option -e, --deploy-environment."""
    mock_runway = mocker.patch(f"{MODULE}.Runway", Mock(spec=Runway, spec_set=True))
    cp_config("min_required", cd_tmp_path)
    runner = CliRunner()
    assert runner.invoke(cli, ["deploy", "-e", "e-option"]).exit_code == 0
    assert mock_runway.call_args.args[1].env.name == "e-option"

    assert (
        runner.invoke(
            cli, ["deploy", "--deploy-environment", "deploy-environment-option"]
        ).exit_code
        == 0
    )
    assert mock_runway.call_args.args[1].env.name == "deploy-environment-option"


def test_deploy_options_tag(
    caplog: pytest.LogCaptureFixture,
    cd_tmp_path: Path,
    cp_config: CpConfigTypeDef,
    mocker: MockerFixture,
) -> None:
    """Test deploy option --tag."""
    caplog.set_level(logging.ERROR, logger="runway.cli.commands.deploy")
    mock_runway = mocker.patch(f"{MODULE}.Runway", Mock(spec=Runway, spec_set=True))
    cp_config("tagged_modules", cd_tmp_path)
    runner = CliRunner()
    result0 = runner.invoke(cli, ["deploy", "--tag", "app:test-app", "--tag", "tier:iac"])
    assert result0.exit_code == 0
    deployment = mock_runway.return_value.deploy.call_args.args[0][0]
    assert len(deployment.modules) == 1
    assert deployment.modules[0].name == "sampleapp-01.cfn"

    assert runner.invoke(cli, ["deploy", "--tag", "app:test-app"]).exit_code == 0
    deployment = mock_runway.return_value.deploy.call_args.args[0][0]
    assert len(deployment.modules) == 3
    assert deployment.modules[0].name == "sampleapp-01.cfn"
    assert deployment.modules[1].name == "sampleapp-02.cfn"
    assert deployment.modules[2].name == "parallel_parent"
    assert len(deployment.modules[2].child_modules) == 1
    assert deployment.modules[2].child_modules[0].name == "sampleapp-03.cfn"

    assert runner.invoke(cli, ["deploy", "--tag", "no-match"]).exit_code == 1
    assert "No modules found with the provided tag(s): no-match" in caplog.messages


def test_deploy_select_deployment(
    cd_tmp_path: Path, cp_config: CpConfigTypeDef, mocker: MockerFixture
) -> None:
    """Test deploy select from two deployments."""
    mock_runway = mocker.patch(f"{MODULE}.Runway", Mock(spec=Runway, spec_set=True))
    cp_config("min_required_multi", cd_tmp_path)
    runner = CliRunner()
    # first value entered is out of range
    result = runner.invoke(cli, ["deploy"], input="35\n1\n")
    assert result.exit_code == 0
    deployments = mock_runway.return_value.deploy.call_args.args[0]
    assert len(deployments) == 1
    assert deployments[0].name == "deployment_1"


def test_deploy_select_deployment_all(
    cd_tmp_path: Path, cp_config: CpConfigTypeDef, mocker: MockerFixture
) -> None:
    """Test deploy select all deployments."""
    mock_runway = mocker.patch(f"{MODULE}.Runway", Mock(spec=Runway, spec_set=True))
    cp_config("min_required_multi", cd_tmp_path)
    runner = CliRunner()
    # first value entered is out of range
    result = runner.invoke(cli, ["deploy"], input="all\n")
    assert result.exit_code == 0
    deployments = mock_runway.return_value.deploy.call_args.args[0]
    assert len(deployments) == 2
    assert deployments[0].name == "deployment_1"
    assert deployments[1].name == "deployment_2"
    assert len(deployments[1].modules) == 2


def test_deploy_select_module(
    cd_tmp_path: Path, cp_config: CpConfigTypeDef, mocker: MockerFixture
) -> None:
    """Test deploy select from two modules."""
    mock_runway = mocker.patch(f"{MODULE}.Runway", Mock(spec=Runway, spec_set=True))
    cp_config("min_required_multi", cd_tmp_path)
    runner = CliRunner()
    # 2nd deployment, out of range, select second module
    result = runner.invoke(cli, ["deploy"], input="2\n35\n2\n")
    assert result.exit_code == 0
    deployment = mock_runway.return_value.deploy.call_args.args[0][0]
    assert len(deployment.modules) == 1
    assert deployment.modules[0].name == "sampleapp-03.cfn"


def test_deploy_select_module_all(
    cd_tmp_path: Path, cp_config: CpConfigTypeDef, mocker: MockerFixture
) -> None:
    """Test deploy select all modules."""
    mock_runway = mocker.patch(f"{MODULE}.Runway", Mock(spec=Runway, spec_set=True))
    cp_config("min_required_multi", cd_tmp_path)
    runner = CliRunner()
    # 2nd deployment, select all
    result = runner.invoke(cli, ["deploy"], input="2\nall\n")
    assert result.exit_code == 0
    deployment = mock_runway.return_value.deploy.call_args.args[0][0]
    assert len(deployment.modules) == 2
    assert deployment.modules[0].name == "sampleapp-02.cfn"
    assert deployment.modules[1].name == "sampleapp-03.cfn"


def test_deploy_select_module_child_modules(
    cd_tmp_path: Path, cp_config: CpConfigTypeDef, mocker: MockerFixture
) -> None:
    """Test deploy select child module."""
    mock_runway = mocker.patch(f"{MODULE}.Runway", Mock(spec=Runway, spec_set=True))
    cp_config("simple_child_modules.1", cd_tmp_path)
    runner = CliRunner()
    # 2nd module, first child
    result = runner.invoke(cli, ["deploy"], input="2\n1\n")
    assert result.exit_code == 0
    deployment = mock_runway.return_value.deploy.call_args.args[0][0]
    assert len(deployment.modules) == 1
    assert deployment.modules[0].name == "parallel-sampleapp-01.cfn"


def test_deploy_select_module_child_modules_all(
    cd_tmp_path: Path, cp_config: CpConfigTypeDef, mocker: MockerFixture
) -> None:
    """Test deploy select all child module."""
    mock_runway = mocker.patch(f"{MODULE}.Runway", Mock(spec=Runway, spec_set=True))
    cp_config("simple_child_modules.1", cd_tmp_path)
    runner = CliRunner()
    # 2nd module, first child
    result = runner.invoke(cli, ["deploy"], input="2\nall\n")
    assert result.exit_code == 0
    deployment = mock_runway.return_value.deploy.call_args.args[0][0]
    assert len(deployment.modules) == 2
    assert deployment.modules[0].name == "parallel-sampleapp-01.cfn"
    assert deployment.modules[1].name == "parallel-sampleapp-02.cfn"


def test_deploy_options_module(
    caplog: pytest.LogCaptureFixture,
    cd_tmp_path: Path,
    cp_config: CpConfigTypeDef,
    mocker: MockerFixture,
) -> None:
    """Test deploy option --module."""
    caplog.set_level(logging.ERROR, logger="runway.cli.utils")
    mock_runway = mocker.patch(f"{MODULE}.Runway", Mock(spec=Runway, spec_set=True))
    cp_config("tagged_modules", cd_tmp_path)
    runner = CliRunner()

    # Exact module name match
    result = runner.invoke(cli, ["deploy", "--module", "sampleapp-01.cfn"])
    assert result.exit_code == 0
    deployment = mock_runway.return_value.deploy.call_args.args[0][0]
    assert len(deployment.modules) == 1
    assert deployment.modules[0].name == "sampleapp-01.cfn"

    # Multiple module names
    result = runner.invoke(
        cli, ["deploy", "--module", "sampleapp-01.cfn", "--module", "sampleapp-02.cfn"]
    )
    assert result.exit_code == 0
    deployment = mock_runway.return_value.deploy.call_args.args[0][0]
    assert len(deployment.modules) == 2
    assert deployment.modules[0].name == "sampleapp-01.cfn"
    assert deployment.modules[1].name == "sampleapp-02.cfn"

    # Glob pattern matching
    result = runner.invoke(cli, ["deploy", "--module", "sampleapp-0*.cfn"])
    assert result.exit_code == 0
    deployment = mock_runway.return_value.deploy.call_args.args[0][0]
    # Should match sampleapp-01.cfn, sampleapp-02.cfn, parallel_parent (with children 03,04,05), sampleapp-06.cfn
    assert len(deployment.modules) == 4
    assert deployment.modules[0].name == "sampleapp-01.cfn"
    assert deployment.modules[1].name == "sampleapp-02.cfn"
    assert deployment.modules[2].name == "parallel_parent"
    assert len(deployment.modules[2].child_modules) == 3
    assert deployment.modules[3].name == "sampleapp-06.cfn"

    # No match error
    result = runner.invoke(cli, ["deploy", "--module", "nonexistent-module"])
    assert result.exit_code == 1
    assert "No modules found matching: nonexistent-module" in caplog.messages


def test_deploy_options_module_child_modules(
    cd_tmp_path: Path,
    cp_config: CpConfigTypeDef,
    mocker: MockerFixture,
) -> None:
    """Test deploy option --module with child modules."""
    mock_runway = mocker.patch(f"{MODULE}.Runway", Mock(spec=Runway, spec_set=True))
    cp_config("tagged_modules", cd_tmp_path)
    runner = CliRunner()

    # Match child module by name - includes parent with only matching children
    result = runner.invoke(cli, ["deploy", "--module", "sampleapp-03.cfn"])
    assert result.exit_code == 0
    deployment = mock_runway.return_value.deploy.call_args.args[0][0]
    assert len(deployment.modules) == 1
    assert deployment.modules[0].name == "parallel_parent"
    assert len(deployment.modules[0].child_modules) == 1
    assert deployment.modules[0].child_modules[0].name == "sampleapp-03.cfn"

    # Match multiple child modules
    result = runner.invoke(
        cli, ["deploy", "--module", "sampleapp-03.cfn", "--module", "sampleapp-04.cfn"]
    )
    assert result.exit_code == 0
    deployment = mock_runway.return_value.deploy.call_args.args[0][0]
    assert len(deployment.modules) == 1
    assert deployment.modules[0].name == "parallel_parent"
    assert len(deployment.modules[0].child_modules) == 2

    # Match parent module by name - includes all children
    result = runner.invoke(cli, ["deploy", "--module", "parallel_parent"])
    assert result.exit_code == 0
    deployment = mock_runway.return_value.deploy.call_args.args[0][0]
    assert len(deployment.modules) == 1
    assert deployment.modules[0].name == "parallel_parent"
    # All 3 children should be included when parent is matched
    assert len(deployment.modules[0].child_modules) == 3


def test_deploy_options_stack(
    cd_tmp_path: Path,
    cp_config: CpConfigTypeDef,
    mocker: MockerFixture,
) -> None:
    """Test deploy option --stack."""
    mock_runway = mocker.patch(f"{MODULE}.Runway", Mock(spec=Runway, spec_set=True))
    cp_config("min_required", cd_tmp_path)
    runner = CliRunner()

    # Verify stack names are passed to context
    result = runner.invoke(cli, ["deploy", "--stack", "vpc-stack", "--stack", "rds-stack"])
    assert result.exit_code == 0

    # Verify the RunwayContext was created with stack_names
    runway_context = mock_runway.call_args.args[1]
    assert runway_context.stack_names == ["vpc-stack", "rds-stack"]


def test_deploy_execute_changesets(
    cd_tmp_path: Path,
    cp_config: CpConfigTypeDef,
    mocker: MockerFixture,
) -> None:
    """Test deploy --execute-changesets with a changeset file."""
    mock_exec = mocker.patch(f"{MODULE}.execute_changesets_from_file")
    cp_config("min_required", cd_tmp_path)

    # Create a changeset file
    cs_file = cd_tmp_path / "changesets.json"
    cs_file.write_text(
        json.dumps(
            {"changesets": [{"stack": "ns-stack1", "changeset_id": "cs-1"}]}
        )
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["deploy", "--execute-changesets", str(cs_file)])
    assert result.exit_code == 0
    mock_exec.assert_called_once()
    # Verify stack_filter is None when no --stack provided
    assert mock_exec.call_args.kwargs.get("stack_filter") is None


def test_deploy_execute_changesets_with_stack_filter(
    cd_tmp_path: Path,
    cp_config: CpConfigTypeDef,
    mocker: MockerFixture,
) -> None:
    """Test deploy --execute-changesets with --stack filter."""
    mock_exec = mocker.patch(f"{MODULE}.execute_changesets_from_file")
    cp_config("min_required", cd_tmp_path)

    cs_file = cd_tmp_path / "changesets.json"
    cs_file.write_text(json.dumps({"changesets": []}))

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["deploy", "--execute-changesets", str(cs_file), "--stack", "vpc-stack"],
    )
    assert result.exit_code == 0
    mock_exec.assert_called_once()
    assert mock_exec.call_args.kwargs.get("stack_filter") == ("vpc-stack",)


def test_deploy_execute_changesets_error(
    caplog: pytest.LogCaptureFixture,
    cd_tmp_path: Path,
    cp_config: CpConfigTypeDef,
    mocker: MockerFixture,
) -> None:
    """Test deploy --execute-changesets handles ChangesetExecutionError."""
    caplog.set_level(logging.ERROR, logger="runway")
    mocker.patch(
        f"{MODULE}.execute_changesets_from_file",
        side_effect=ChangesetExecutionError("my-stack", "cs-1", "bad status"),
    )
    cp_config("min_required", cd_tmp_path)

    cs_file = cd_tmp_path / "changesets.json"
    cs_file.write_text(json.dumps({"changesets": []}))

    runner = CliRunner()
    result = runner.invoke(cli, ["deploy", "--execute-changesets", str(cs_file)])
    assert result.exit_code == 1


def test_deploy_execute_changesets_file_not_found(
    caplog: pytest.LogCaptureFixture,
    cd_tmp_path: Path,
    cp_config: CpConfigTypeDef,
) -> None:
    """Test deploy --execute-changesets with nonexistent file."""
    caplog.set_level(logging.ERROR, logger="runway")
    cp_config("min_required", cd_tmp_path)

    runner = CliRunner()
    # Click's type=click.Path(exists=True) will catch this before the command runs
    result = runner.invoke(cli, ["deploy", "--execute-changesets", "/tmp/nonexistent.json"])
    assert result.exit_code != 0
