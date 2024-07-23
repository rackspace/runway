"""Test ``runway init`` command.

The below tests only cover the CLI.
Runway's core logic has been mocked out to test on separately from the CLI.

"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from unittest.mock import Mock

from click.testing import CliRunner
from pydantic import ValidationError

from runway._cli import cli
from runway.config import RunwayConfig
from runway.context import RunwayContext
from runway.core import Runway
from runway.exceptions import ConfigNotFound

if TYPE_CHECKING:
    from pathlib import Path

    import pytest
    from pytest_mock import MockerFixture

    from ...conftest import CpConfigTypeDef

MODULE = "runway._cli.commands._init"


def test_init(
    cd_tmp_path: Path,
    cp_config: CpConfigTypeDef,
    caplog: pytest.LogCaptureFixture,
    mocker: MockerFixture,
) -> None:
    """Test init."""
    mock_runway = mocker.patch(f"{MODULE}.Runway", Mock(spec=Runway, spec_set=True))
    caplog.set_level(logging.INFO, logger="runway")
    cp_config("min_required", cd_tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["init"])
    assert result.exit_code == 0

    mock_runway.assert_called_once()
    assert isinstance(mock_runway.call_args.args[0], RunwayConfig)
    assert isinstance(mock_runway.call_args.args[1], RunwayContext)

    inst = mock_runway.return_value
    inst.init.assert_called_once()
    assert len(inst.init.call_args.args[0]) == 1


def test_init_handle_validation_error(
    cd_tmp_path: Path,
    cp_config: CpConfigTypeDef,
    mocker: MockerFixture,
) -> None:
    """Test init handle ValidationError."""
    mocker.patch(
        f"{MODULE}.Runway",
        spec=Runway,
        spec_set=True,
        init=Mock(side_effect=ValidationError([], Mock())),  # type: ignore
    )
    cp_config("min_required", cd_tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["init"])
    assert result.exit_code == 1
    assert "ValidationError" in result.output


def test_init_handle_config_not_found(
    cd_tmp_path: Path,
    cp_config: CpConfigTypeDef,
    mocker: MockerFixture,
) -> None:
    """Test init handle ConfigNotFound."""
    mocker.patch(
        f"{MODULE}.Runway",
        spec=Runway,
        spec_set=True,
        side_effect=Mock(side_effect=ConfigNotFound(path=cd_tmp_path)),
    )
    cp_config("min_required", cd_tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["init"])
    assert result.exit_code == 1
    assert "config file not found" in result.output


def test_init_options_ci(
    cd_tmp_path: Path, cp_config: CpConfigTypeDef, mocker: MockerFixture
) -> None:
    """Test init option --ci."""
    mock_runway = mocker.patch(f"{MODULE}.Runway", Mock(spec=Runway, spec_set=True))
    cp_config("min_required", cd_tmp_path)
    runner = CliRunner()
    assert runner.invoke(cli, ["init", "--ci"]).exit_code == 0
    assert mock_runway.call_args.args[1].env.ci is True

    assert runner.invoke(cli, ["init"]).exit_code == 0
    assert mock_runway.call_args.args[1].env.ci is False


def test_init_options_deploy_environment(
    cd_tmp_path: Path, cp_config: CpConfigTypeDef, mocker: MockerFixture
) -> None:
    """Test init option -e, --deploy-environment."""
    mock_runway = mocker.patch(f"{MODULE}.Runway", Mock(spec=Runway, spec_set=True))
    cp_config("min_required", cd_tmp_path)
    runner = CliRunner()
    assert runner.invoke(cli, ["init", "-e", "e-option"]).exit_code == 0
    assert mock_runway.call_args.args[1].env.name == "e-option"

    assert (
        runner.invoke(cli, ["init", "--deploy-environment", "deploy-environment-option"]).exit_code
        == 0
    )
    assert mock_runway.call_args.args[1].env.name == "deploy-environment-option"


def test_init_options_tag(
    caplog: pytest.LogCaptureFixture,
    cd_tmp_path: Path,
    cp_config: CpConfigTypeDef,
    mocker: MockerFixture,
) -> None:
    """Test init option --tag."""
    mock_runway = mocker.patch(f"{MODULE}.Runway", Mock(spec=Runway, spec_set=True))
    caplog.set_level(logging.ERROR, logger="runway.cli.commands.init")
    cp_config("tagged_modules", cd_tmp_path)
    runner = CliRunner()
    result0 = runner.invoke(cli, ["init", "--tag", "app:test-app", "--tag", "tier:iac"])
    assert result0.exit_code == 0
    deployment = mock_runway.return_value.init.call_args.args[0][0]
    assert len(deployment.modules) == 1
    assert deployment.modules[0].name == "sampleapp-01.cfn"

    assert runner.invoke(cli, ["init", "--tag", "app:test-app"]).exit_code == 0
    deployment = mock_runway.return_value.init.call_args.args[0][0]
    assert len(deployment.modules) == 3
    assert deployment.modules[0].name == "sampleapp-01.cfn"
    assert deployment.modules[1].name == "sampleapp-02.cfn"
    assert deployment.modules[2].name == "parallel_parent"
    assert len(deployment.modules[2].child_modules) == 1
    assert deployment.modules[2].child_modules[0].name == "sampleapp-03.cfn"

    assert runner.invoke(cli, ["init", "--tag", "no-match"]).exit_code == 1
    assert "No modules found with the provided tag(s): no-match" in caplog.messages


def test_init_select_deployment(
    cd_tmp_path: Path, cp_config: CpConfigTypeDef, mocker: MockerFixture
) -> None:
    """Test init select from two deployments."""
    mock_runway = mocker.patch(f"{MODULE}.Runway", Mock(spec=Runway, spec_set=True))
    cp_config("min_required_multi", cd_tmp_path)
    runner = CliRunner()
    # first value entered is out of range
    result = runner.invoke(cli, ["init"], input="35\n1\n")
    assert result.exit_code == 0
    deployments = mock_runway.return_value.init.call_args.args[0]
    assert len(deployments) == 1
    assert deployments[0].name == "deployment_1"


def test_init_select_deployment_all(
    cd_tmp_path: Path, cp_config: CpConfigTypeDef, mocker: MockerFixture
) -> None:
    """Test init select all deployments."""
    mock_runway = mocker.patch(f"{MODULE}.Runway", Mock(spec=Runway, spec_set=True))
    cp_config("min_required_multi", cd_tmp_path)
    runner = CliRunner()
    # first value entered is out of range
    result = runner.invoke(cli, ["init"], input="all\n")
    assert result.exit_code == 0
    deployments = mock_runway.return_value.init.call_args.args[0]
    assert len(deployments) == 2
    assert deployments[0].name == "deployment_1"
    assert deployments[1].name == "deployment_2"
    assert len(deployments[1].modules) == 2


def test_init_select_module(
    cd_tmp_path: Path, cp_config: CpConfigTypeDef, mocker: MockerFixture
) -> None:
    """Test init select from two modules."""
    mock_runway = mocker.patch(f"{MODULE}.Runway", Mock(spec=Runway, spec_set=True))
    cp_config("min_required_multi", cd_tmp_path)
    runner = CliRunner()
    # 2nd deployment, out of range, select second module
    result = runner.invoke(cli, ["init"], input="2\n35\n2\n")
    assert result.exit_code == 0
    deployment = mock_runway.return_value.init.call_args.args[0][0]
    assert len(deployment.modules) == 1
    assert deployment.modules[0].name == "sampleapp-03.cfn"


def test_init_select_module_all(
    cd_tmp_path: Path, cp_config: CpConfigTypeDef, mocker: MockerFixture
) -> None:
    """Test init select all modules."""
    mock_runway = mocker.patch(f"{MODULE}.Runway", Mock(spec=Runway, spec_set=True))
    cp_config("min_required_multi", cd_tmp_path)
    runner = CliRunner()
    # 2nd deployment, select all
    result = runner.invoke(cli, ["init"], input="2\nall\n")
    assert result.exit_code == 0
    deployment = mock_runway.return_value.init.call_args.args[0][0]
    assert len(deployment.modules) == 2
    assert deployment.modules[0].name == "sampleapp-02.cfn"
    assert deployment.modules[1].name == "sampleapp-03.cfn"


def test_init_select_module_child_modules(
    cd_tmp_path: Path, cp_config: CpConfigTypeDef, mocker: MockerFixture
) -> None:
    """Test init select child module."""
    mock_runway = mocker.patch(f"{MODULE}.Runway", Mock(spec=Runway, spec_set=True))
    cp_config("simple_child_modules.1", cd_tmp_path)
    runner = CliRunner()
    # 2nd module, first child
    result = runner.invoke(cli, ["init"], input="2\n1\n")
    assert result.exit_code == 0
    deployment = mock_runway.return_value.init.call_args.args[0][0]
    assert len(deployment.modules) == 1
    assert deployment.modules[0].name == "parallel-sampleapp-01.cfn"


def test_init_select_module_child_modules_all(
    cd_tmp_path: Path, cp_config: CpConfigTypeDef, mocker: MockerFixture
) -> None:
    """Test init select all child module."""
    mock_runway = mocker.patch(f"{MODULE}.Runway", Mock(spec=Runway, spec_set=True))
    cp_config("simple_child_modules.1", cd_tmp_path)
    runner = CliRunner()
    # 2nd module, first child
    result = runner.invoke(cli, ["init"], input="2\nall\n")
    assert result.exit_code == 0
    deployment = mock_runway.return_value.init.call_args.args[0][0]
    assert len(deployment.modules) == 2
    assert deployment.modules[0].name == "parallel-sampleapp-01.cfn"
    assert deployment.modules[1].name == "parallel-sampleapp-02.cfn"
