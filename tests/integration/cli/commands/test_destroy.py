"""Test ``runway destroy``.

The below tests only cover the CLI.
Runway's core logic has been mocked out to test on separately from the CLI.

"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from click.testing import CliRunner
from mock import Mock

from runway._cli import cli
from runway.config import RunwayConfig
from runway.context import RunwayContext
from runway.core import Runway

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import LogCaptureFixture, MonkeyPatch
    from pytest_mock import MockerFixture

    from ...conftest import CpConfigTypeDef

MODULE = "runway._cli.commands._destroy"


def test_destroy(cd_tmp_path: Path, cp_config: CpConfigTypeDef, mocker: MockerFixture) -> None:
    """Test destroy."""
    mock_runway = mocker.patch(f"{MODULE}.Runway", Mock(spec=Runway))
    cp_config("min_required", cd_tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["destroy"], input="y\ny\n")
    assert result.exit_code == 0

    mock_runway.assert_called_once()
    assert isinstance(mock_runway.call_args.args[0], RunwayConfig)
    assert isinstance(mock_runway.call_args.args[1], RunwayContext)

    mock_runway.reverse_deployments.assert_called_once()
    assert len(mock_runway.reverse_deployments.call_args.args[0]) == 1  # type: ignore
    inst = mock_runway.return_value
    inst.destroy.assert_called_once_with(mock_runway.reverse_deployments.return_value)


def test_destroy_no(cd_tmp_path: Path, cp_config: CpConfigTypeDef) -> None:
    """Test destroy without proceeding."""
    cp_config("min_required", cd_tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["destroy"], input="n\n")
    assert result.exit_code == 0
    assert result.output == (
        "[WARNING] Runway is about to be run in DESTROY mode. [WARNING]\n"
        "Any/all deployment(s) selected will be irrecoverably DESTROYED.\n"
        "\nProceed? [y/N]: n\n"
    )


def test_destroy_options_ci(
    cd_tmp_path: Path, cp_config: CpConfigTypeDef, mocker: MockerFixture
) -> None:
    """Test destroy option --ci."""
    mock_runway = mocker.patch(f"{MODULE}.Runway", Mock(spec=Runway))
    cp_config("min_required", cd_tmp_path)
    runner = CliRunner()
    assert runner.invoke(cli, ["destroy", "--ci"]).exit_code == 0
    assert mock_runway.call_args.args[1].env.ci is True

    assert runner.invoke(cli, ["destroy"], input="y\ny\n").exit_code == 0
    assert mock_runway.call_args.args[1].env.ci is False


def test_destroy_options_deploy_environment(
    cd_tmp_path: Path, cp_config: CpConfigTypeDef, mocker: MockerFixture
) -> None:
    """Test destroy option -e, --deploy-environment."""
    mock_runway = mocker.patch(f"{MODULE}.Runway", Mock(spec=Runway))
    cp_config("min_required", cd_tmp_path)
    runner = CliRunner()
    assert runner.invoke(cli, ["destroy", "-e", "e-option"], input="y\ny\n").exit_code == 0
    assert mock_runway.call_args.args[1].env.name == "e-option"

    assert (
        runner.invoke(
            cli,
            ["destroy", "--deploy-environment", "deploy-environment-option"],
            input="y\ny\n",
        ).exit_code
        == 0
    )
    assert mock_runway.call_args.args[1].env.name == "deploy-environment-option"


def test_destroy_options_tag(
    caplog: LogCaptureFixture,
    cd_tmp_path: Path,
    cp_config: CpConfigTypeDef,
    monkeypatch: MonkeyPatch,
) -> None:
    """Test destroy option --tag."""
    caplog.set_level(logging.ERROR, logger="runway.cli.commands.destroy")
    cp_config("tagged_modules", cd_tmp_path)
    mock_destroy = Mock()
    monkeypatch.setattr(MODULE + ".Runway.destroy", mock_destroy)
    runner = CliRunner()
    assert (
        runner.invoke(
            cli, ["destroy", "--tag", "app:test-app", "--tag", "tier:iac"], input="y\n"
        ).exit_code
        == 0
    )
    deployment = mock_destroy.call_args.args[0][0]
    assert len(deployment.modules) == 1
    assert deployment.modules[0].name == "sampleapp-01.cfn"

    assert runner.invoke(cli, ["destroy", "--tag", "app:test-app"], input="y\n").exit_code == 0
    deployment = mock_destroy.call_args.args[0][0]
    assert len(deployment.modules) == 3
    assert deployment.modules[0].name == "parallel_parent"
    assert len(deployment.modules[0].child_modules) == 1
    assert deployment.modules[0].child_modules[0].name == "sampleapp-03.cfn"
    assert deployment.modules[1].name == "sampleapp-02.cfn"
    assert deployment.modules[2].name == "sampleapp-01.cfn"

    assert runner.invoke(cli, ["destroy", "--tag", "no-match"], input="y\n").exit_code == 1
    assert "No modules found with the provided tag(s): no-match" in caplog.messages


def test_destroy_select_deployment(
    cd_tmp_path: Path, cp_config: CpConfigTypeDef, monkeypatch: MonkeyPatch
) -> None:
    """Test destroy select from two deployments."""
    cp_config("min_required_multi", cd_tmp_path)
    mock_destroy = Mock()
    monkeypatch.setattr(MODULE + ".Runway.destroy", mock_destroy)
    runner = CliRunner()
    # first value entered is out of range
    assert runner.invoke(cli, ["destroy"], input="y\n35\n1\nn\n").exit_code == 0
    mock_destroy.assert_not_called()

    assert runner.invoke(cli, ["destroy"], input="y\n1\ny\n").exit_code == 0
    deployments = mock_destroy.call_args.args[0]
    assert len(deployments) == 1
    assert deployments[0].name == "deployment_1"


def test_destroy_select_deployment_all(
    cd_tmp_path: Path, cp_config: CpConfigTypeDef, monkeypatch: MonkeyPatch
) -> None:
    """Test destroy select all deployments."""
    cp_config("min_required_multi", cd_tmp_path)
    mock_destroy = Mock()
    monkeypatch.setattr(MODULE + ".Runway.destroy", mock_destroy)
    runner = CliRunner()
    # first value entered is out of range
    result = runner.invoke(cli, ["destroy"], input="y\nall\n")
    assert result.exit_code == 0
    deployments = mock_destroy.call_args.args[0]
    assert len(deployments) == 2
    assert deployments[0].name == "deployment_2"
    assert len(deployments[0].modules) == 2
    assert deployments[1].name == "deployment_1"


def test_destroy_select_module(
    cd_tmp_path: Path, cp_config: CpConfigTypeDef, monkeypatch: MonkeyPatch
) -> None:
    """Test destroy select from two modules."""
    cp_config("min_required_multi", cd_tmp_path)
    mock_destroy = Mock()
    monkeypatch.setattr(MODULE + ".Runway.destroy", mock_destroy)
    runner = CliRunner()
    # 2nd deployment, out of range, select second module
    result = runner.invoke(cli, ["destroy"], input="y\n2\n35\n2\n")
    assert result.exit_code == 0
    deployment = mock_destroy.call_args.args[0][0]
    assert len(deployment.modules) == 1
    assert deployment.modules[0].name == "sampleapp-03.cfn"


def test_destroy_select_module_all(
    cd_tmp_path: Path, cp_config: CpConfigTypeDef, monkeypatch: MonkeyPatch
) -> None:
    """Test destroy select all modules."""
    cp_config("min_required_multi", cd_tmp_path)
    mock_destroy = Mock()
    monkeypatch.setattr(MODULE + ".Runway.destroy", mock_destroy)
    runner = CliRunner()
    # 2nd deployment, select all
    result = runner.invoke(cli, ["destroy"], input="y\n2\nall\n")
    assert result.exit_code == 0
    deployment = mock_destroy.call_args.args[0][0]
    assert len(deployment.modules) == 2
    assert deployment.modules[0].name == "sampleapp-03.cfn"
    assert deployment.modules[1].name == "sampleapp-02.cfn"


def test_destroy_select_module_child_modules(
    cd_tmp_path: Path, cp_config: CpConfigTypeDef, monkeypatch: MonkeyPatch
) -> None:
    """Test destroy select child module."""
    cp_config("simple_child_modules.1", cd_tmp_path)
    mock_destroy = Mock()
    monkeypatch.setattr(MODULE + ".Runway.destroy", mock_destroy)
    runner = CliRunner()
    # 2nd module, first child
    result = runner.invoke(cli, ["destroy"], input="y\n2\n1\n")
    assert result.exit_code == 0
    deployment = mock_destroy.call_args.args[0][0]
    assert len(deployment.modules) == 1
    assert deployment.modules[0].name == "parallel-sampleapp-01.cfn"


def test_destroy_select_module_child_modules_all(
    cd_tmp_path: Path, cp_config: CpConfigTypeDef, monkeypatch: MonkeyPatch
) -> None:
    """Test destroy select all child module."""
    cp_config("simple_child_modules.1", cd_tmp_path)
    mock_destroy = Mock()
    monkeypatch.setattr(MODULE + ".Runway.destroy", mock_destroy)
    runner = CliRunner()
    # 2nd module, first child
    result = runner.invoke(cli, ["destroy"], input="y\n2\nall\n")
    assert result.exit_code == 0
    deployment = mock_destroy.call_args.args[0][0]
    assert len(deployment.modules) == 2
    assert deployment.modules[0].name == "parallel-sampleapp-02.cfn"
    assert deployment.modules[1].name == "parallel-sampleapp-01.cfn"
