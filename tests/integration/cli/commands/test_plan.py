"""Test ``runway plan``.

The below tests only cover the CLI.
Runway's core logic has been mocked out to test on separately from the CLI.

"""
import logging

from click.testing import CliRunner
from mock import patch

from runway._cli import cli
from runway.config import Config
from runway.context import Context
from runway.core import Runway

MODULE = "runway._cli.commands._plan"


@patch(MODULE + ".Runway", spec=Runway, spec_set=True)
def test_plan(mock_runway, cd_tmp_path, cp_config):
    """Test plan."""
    cp_config("min_required", cd_tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["plan"])
    assert result.exit_code == 0

    mock_runway.assert_called_once()
    assert isinstance(mock_runway.call_args.args[0], Config)
    assert isinstance(mock_runway.call_args.args[1], Context)

    inst = mock_runway.return_value
    inst.plan.assert_called_once()
    assert len(inst.plan.call_args.args[0]) == 1


@patch(MODULE + ".Runway", spec=Runway, spec_set=True)
def test_plan_options_ci(mock_runway, cd_tmp_path, cp_config):
    """Test plan option --ci."""
    cp_config("min_required", cd_tmp_path)
    runner = CliRunner()
    assert runner.invoke(cli, ["plan", "--ci"]).exit_code == 0
    assert mock_runway.call_args.args[1].env.ci is True

    assert runner.invoke(cli, ["plan"]).exit_code == 0
    assert mock_runway.call_args.args[1].env.ci is False


@patch(MODULE + ".Runway", spec=Runway, spec_set=True)
def test_plan_options_deploy_environment(mock_runway, cd_tmp_path, cp_config):
    """Test plan option -e, --deploy-environment."""
    cp_config("min_required", cd_tmp_path)
    runner = CliRunner()
    assert runner.invoke(cli, ["plan", "-e", "e-option"]).exit_code == 0
    assert mock_runway.call_args.args[1].env.name == "e-option"

    assert (
        runner.invoke(
            cli, ["plan", "--deploy-environment", "deploy-environment-option"]
        ).exit_code
        == 0
    )
    assert mock_runway.call_args.args[1].env.name == "deploy-environment-option"


@patch(MODULE + ".Runway", spec=Runway, spec_set=True)
def test_plan_options_tag(mock_runway, caplog, cd_tmp_path, cp_config):
    """Test plan option --tag."""
    caplog.set_level(logging.ERROR, logger="runway.cli.commands.plan")
    cp_config("tagged_modules", cd_tmp_path)
    runner = CliRunner()
    assert (
        runner.invoke(
            cli, ["plan", "--tag", "app:test-app", "--tag", "tier:iac"]
        ).exit_code
        == 0
    )
    deployment = mock_runway.return_value.plan.call_args.args[0][0]
    assert len(deployment.modules) == 1
    assert deployment.modules[0].name == "sampleapp-01.cfn"

    assert runner.invoke(cli, ["plan", "--tag", "app:test-app"]).exit_code == 0
    deployment = mock_runway.return_value.plan.call_args.args[0][0]
    assert len(deployment.modules) == 3
    assert deployment.modules[0].name == "sampleapp-01.cfn"
    assert deployment.modules[1].name == "sampleapp-02.cfn"
    assert deployment.modules[2].name == "parallel_parent"
    assert len(deployment.modules[2].child_modules) == 1
    assert deployment.modules[2].child_modules[0].name == "sampleapp-03.cfn"

    assert runner.invoke(cli, ["plan", "--tag", "no-match"]).exit_code == 1
    assert "No modules found with the provided tag(s): no-match" in caplog.messages


@patch(MODULE + ".Runway", spec=Runway, spec_set=True)
def test_plan_select_deployment(mock_runway, cd_tmp_path, cp_config):
    """Test plan select from two deployments."""
    cp_config("min_required_multi", cd_tmp_path)
    runner = CliRunner()
    # first value entered is out of range
    result = runner.invoke(cli, ["plan"], input="35\n1\n")
    assert result.exit_code == 0
    deployments = mock_runway.return_value.plan.call_args.args[0]
    assert len(deployments) == 1
    assert deployments[0].name == "deployment_1"


@patch(MODULE + ".Runway", spec=Runway, spec_set=True)
def test_plan_select_deployment_all(mock_runway, cd_tmp_path, cp_config):
    """Test plan select all deployments."""
    cp_config("min_required_multi", cd_tmp_path)
    runner = CliRunner()
    # first value entered is out of range
    result = runner.invoke(cli, ["plan"], input="all\n")
    assert result.exit_code == 0
    deployments = mock_runway.return_value.plan.call_args.args[0]
    assert len(deployments) == 2
    assert deployments[0].name == "deployment_1"
    assert deployments[1].name == "deployment_2"
    assert len(deployments[1].modules) == 2


@patch(MODULE + ".Runway", spec=Runway, spec_set=True)
def test_plan_select_module(mock_runway, cd_tmp_path, cp_config):
    """Test plan select from two modules."""
    cp_config("min_required_multi", cd_tmp_path)
    runner = CliRunner()
    # 2nd deployment, out of range, select second module
    result = runner.invoke(cli, ["plan"], input="2\n35\n2\n")
    assert result.exit_code == 0
    deployment = mock_runway.return_value.plan.call_args.args[0][0]
    assert len(deployment.modules) == 1
    assert deployment.modules[0].name == "sampleapp-03.cfn"


@patch(MODULE + ".Runway", spec=Runway, spec_set=True)
def test_plan_select_module_all(mock_runway, cd_tmp_path, cp_config):
    """Test plan select all modules."""
    cp_config("min_required_multi", cd_tmp_path)
    runner = CliRunner()
    # 2nd deployment, select all
    result = runner.invoke(cli, ["plan"], input="2\nall\n")
    assert result.exit_code == 0
    deployment = mock_runway.return_value.plan.call_args.args[0][0]
    assert len(deployment.modules) == 2
    assert deployment.modules[0].name == "sampleapp-02.cfn"
    assert deployment.modules[1].name == "sampleapp-03.cfn"


@patch(MODULE + ".Runway", spec=Runway, spec_set=True)
def test_plan_select_module_child_modules(mock_runway, cd_tmp_path, cp_config):
    """Test plan select child module."""
    cp_config("simple_child_modules.1", cd_tmp_path)
    runner = CliRunner()
    # 2nd module, first child
    result = runner.invoke(cli, ["plan"], input="2\n1\n")
    assert result.exit_code == 0
    deployment = mock_runway.return_value.plan.call_args.args[0][0]
    assert len(deployment.modules) == 1
    assert deployment.modules[0].name == "parallel-sampleapp-01.cfn"


@patch(MODULE + ".Runway", spec=Runway, spec_set=True)
def test_plan_select_module_child_modules_all(mock_runway, cd_tmp_path, cp_config):
    """Test plan select all child module."""
    cp_config("simple_child_modules.1", cd_tmp_path)
    runner = CliRunner()
    # 2nd module, first child
    result = runner.invoke(cli, ["plan"], input="2\nall\n")
    assert result.exit_code == 0
    deployment = mock_runway.return_value.plan.call_args.args[0][0]
    assert len(deployment.modules) == 2
    assert deployment.modules[0].name == "parallel-sampleapp-01.cfn"
    assert deployment.modules[1].name == "parallel-sampleapp-02.cfn"
