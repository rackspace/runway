"""Test runway.module.terraform."""
# pylint: disable=no-self-use,too-many-statements,too-many-lines
# pyright: basic, reportFunctionMemberAccess=none
from __future__ import annotations

import json
import logging
import subprocess
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, Union

import pytest
from mock import MagicMock, Mock

from runway._logging import LogLevels
from runway.module.terraform import (
    Terraform,
    TerraformBackendConfig,
    TerraformOptions,
    gen_workspace_tfvars_files,
    update_env_vars_with_tf_var_values,
)
from runway.utils import Version

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import LogCaptureFixture, MonkeyPatch
    from pytest_mock import MockerFixture

    from ..factories import MockRunwayContext

MODULE = "runway.module.terraform"


def test_gen_workspace_tfvars_files() -> None:
    """Test gen_workspace_tfvars_files."""
    assert gen_workspace_tfvars_files("test", "us-east-1") == [
        "test-us-east-1.tfvars",
        "test.tfvars",
    ]


def test_update_env_vars_with_tf_var_values() -> None:
    """Test update_env_vars_with_tf_var_values."""
    result = update_env_vars_with_tf_var_values(
        {},
        {
            "foo": "bar",
            "list": ["foo", 1, True],
            "map": {"one": "two", "three": "four"},
        },
    )
    expected = {
        "TF_VAR_foo": "bar",
        "TF_VAR_list": '["foo", 1, true]',
        "TF_VAR_map": '{ one = "two", three = "four" }',
    }

    assert result == expected


class TestTerraform:  # pylint: disable=too-many-public-methods
    """Test runway.module.terraform.Terraform."""

    def test___init__(self, runway_context: MockRunwayContext, tmp_path: Path) -> None:
        """Test __init__."""
        parameters = {"key1": "val1"}
        obj = Terraform(
            runway_context,
            explicitly_enabled=True,
            module_root=tmp_path,
            parameters=parameters,
        )

        assert obj.logger
        assert obj.path == tmp_path
        assert obj.explicitly_enabled
        assert isinstance(obj.options, TerraformOptions)
        assert obj.parameters == parameters
        assert obj.required_workspace == runway_context.env.name

    def test___init___options_workspace(
        self, runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test __init__ with workspace option."""
        options = {"terraform_workspace": "default"}
        obj = Terraform(runway_context, module_root=tmp_path, options=options)
        assert obj.required_workspace == options["terraform_workspace"]

    def test_auto_tfvars(
        self,
        caplog: LogCaptureFixture,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test auto_tfvars."""
        caplog.set_level(LogLevels.DEBUG, logger=MODULE)
        mocker.patch.object(Terraform, "version", Version("0.15.5"))
        options = {
            "terraform_write_auto_tfvars": True,
        }
        parameters = {"key": "val"}
        obj = Terraform(
            runway_context, module_root=tmp_path, options=options, parameters=parameters
        )
        assert obj.auto_tfvars.is_file()
        assert json.loads(obj.auto_tfvars.read_text()) == parameters
        assert "unable to parse current version" not in "\n".join(caplog.messages)

        # check cases where the file will not be written
        obj.auto_tfvars.unlink()
        del obj.auto_tfvars
        obj.options.write_auto_tfvars = False
        assert not obj.auto_tfvars.exists()  # type: ignore

        del obj.auto_tfvars
        obj.options.write_auto_tfvars = True
        obj.parameters = {}
        assert not obj.auto_tfvars.exists()  # type: ignore

    def test_auto_tfvars_unsupported_version(
        self,
        caplog: LogCaptureFixture,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test auto_tfvars with a version that does not support it."""
        caplog.set_level(LogLevels.WARNING, logger=MODULE)
        mocker.patch.object(Terraform, "version", Version("0.9.0"))
        options = {"terraform_write_auto_tfvars": True}
        parameters = {"key": "val"}
        obj = Terraform(
            runway_context, module_root=tmp_path, options=options, parameters=parameters
        )
        assert obj.auto_tfvars.is_file()
        assert json.loads(obj.auto_tfvars.read_text()) == parameters
        assert (
            "Terraform version does not support the use of "
            "*.auto.tfvars; some variables may be missing"
        ) in "\n".join(caplog.messages)

    def test_cleanup_dot_terraform(
        self,
        caplog: LogCaptureFixture,
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test cleanup_dot_terraform."""
        caplog.set_level(logging.DEBUG, logger=MODULE)
        obj = Terraform(runway_context, module_root=tmp_path)

        obj.cleanup_dot_terraform()
        assert "skipped cleanup" in "\n".join(caplog.messages)

        dot_tf = tmp_path / ".terraform"
        dot_tf_modules = dot_tf / "modules"
        dot_tf_modules.mkdir(parents=True)
        (dot_tf_modules / "some_file").touch()
        dot_tf_plugins = dot_tf / "plugins"
        dot_tf_plugins.mkdir(parents=True)
        (dot_tf_plugins / "some_file").touch()
        dot_tf_tfstate = dot_tf / "terraform.tfstate"
        dot_tf_tfstate.touch()

        obj.cleanup_dot_terraform()
        assert dot_tf.exists()
        assert not dot_tf_modules.exists()
        assert dot_tf_plugins.exists()
        assert (dot_tf_plugins / "some_file").exists()
        assert not dot_tf_tfstate.exists()
        assert "removing some of its contents" in "\n".join(caplog.messages)

    def test_current_workspace(
        self, mocker: MockerFixture, runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test current_workspace."""
        mock_terraform_workspace_show = mocker.patch.object(
            Terraform, "terraform_workspace_show", return_value="default"
        )
        assert (
            Terraform(runway_context, module_root=tmp_path).current_workspace
            == "default"
        )
        mock_terraform_workspace_show.assert_called_once_with()

    @pytest.mark.parametrize(
        "filename, expected",
        [
            ("test-us-east-1.tfvars", "test-us-east-1.tfvars"),
            ("test.tfvars", "test.tfvars"),
            (["test-us-east-1.tfvars", "test.tfvars"], "test-us-east-1.tfvars"),
            ([], None),
        ],
    )
    def test_env_file(
        self,
        filename: Union[List[str], str],
        expected: Optional[str],
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test env_file."""
        obj = Terraform(runway_context, module_root=tmp_path)

        if isinstance(filename, list):
            for name in filename:
                (tmp_path / name).touch()
        else:
            (tmp_path / filename).touch()
        if expected:
            assert obj.env_file == ["-var-file=" + expected]
        else:
            assert not obj.env_file

    @pytest.mark.parametrize("action", ["deploy", "destroy", "init", "plan"])
    def test_execute(
        self,
        action: str,
        caplog: LogCaptureFixture,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test executing a Runway action."""
        caplog.set_level(LogLevels.DEBUG, logger=MODULE)
        mocker.patch.object(Terraform, "handle_backend", MagicMock())
        mocker.patch.object(Terraform, "skip", True)
        mocker.patch.object(Terraform, "cleanup_dot_terraform", MagicMock())
        mocker.patch.object(Terraform, "handle_parameters", MagicMock())
        mocker.patch.object(Terraform, "terraform_init", MagicMock())
        mocker.patch.object(Terraform, "current_workspace", "test")
        mocker.patch.object(
            Terraform, "terraform_workspace_list", MagicMock(return_value="* test")
        )
        mocker.patch.object(Terraform, "terraform_workspace_select", MagicMock())
        mocker.patch.object(Terraform, "terraform_workspace_new", MagicMock())
        mocker.patch.object(Terraform, "terraform_get", MagicMock())
        mocker.patch.object(Terraform, "terraform_apply", MagicMock())
        mocker.patch.object(Terraform, "terraform_destroy", MagicMock())
        mocker.patch.object(Terraform, "terraform_plan", MagicMock())
        mocker.patch.object(
            Terraform,
            "auto_tfvars",
            MagicMock(exists=MagicMock(return_value=True), unlink=MagicMock()),
        )
        command = "apply" if action == "deploy" else action

        # pylint: disable=no-member
        # module is skipped
        obj = Terraform(runway_context, module_root=tmp_path)
        assert not obj[action]()
        obj.handle_backend.assert_called_once_with()
        obj.cleanup_dot_terraform.assert_not_called()
        obj.handle_parameters.assert_not_called()
        obj.auto_tfvars.exists.assert_called_once_with()
        obj.auto_tfvars.unlink.assert_called_once_with()
        caplog.clear()

        # module is run; workspace matches
        obj.auto_tfvars.exists.return_value = False
        mocker.patch.object(obj, "skip", False)
        assert not obj[action]()
        obj.cleanup_dot_terraform.assert_called_once_with()
        obj.handle_parameters.assert_called_once_with()
        obj.terraform_init.assert_called_once_with()
        obj.terraform_workspace_list.assert_not_called()
        obj.terraform_workspace_select.assert_not_called()
        obj.terraform_workspace_new.assert_not_called()
        obj.terraform_get.assert_called_once_with()
        obj["terraform_" + command].assert_called_once_with()
        assert obj.auto_tfvars.exists.call_count == 2
        assert obj.auto_tfvars.unlink.call_count == 1
        logs = "\n".join(caplog.messages)
        assert "init (in progress)" in logs
        assert "init (complete)" in logs
        assert "re-running init after workspace change..." not in logs
        assert f"{command} (in progress)" in logs
        assert f"{command} (complete)" in logs
        caplog.clear()

        # module is run; switch to workspace
        mocker.patch.object(Terraform, "current_workspace", "default")
        assert not obj[action]()
        obj.terraform_workspace_list.assert_called_once_with()
        obj.terraform_workspace_select.assert_called_once_with("test")
        obj.terraform_workspace_new.assert_not_called()
        logs = "\n".join(caplog.messages)
        assert "re-running init after workspace change..." in logs

        # module is run; create workspace
        mocker.patch.object(
            Terraform, "terraform_workspace_list", MagicMock(return_value="")
        )
        assert not obj[action]()
        obj.terraform_workspace_new.assert_called_once_with("test")

    @pytest.mark.parametrize(
        "command, args_list, expected",
        [
            (
                "init",
                ["-backend-config", "bucket=name"],
                ["init", "-backend-config", "bucket=name"],
            ),
            (["workspace", "list"], None, ["workspace", "list"]),
            (["workspace", "new"], ["test"], ["workspace", "new", "test"]),
        ],
    )
    def test_gen_command(
        self,
        command: Union[List[str], str],
        args_list: Optional[List[str]],
        expected: List[str],
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test gen_command."""
        mocker.patch.object(Terraform, "tf_bin", "terraform")
        expected.insert(0, "terraform")

        obj = Terraform(runway_context, module_root=tmp_path)
        mocker.patch.object(obj.ctx, "no_color", False)
        assert obj.gen_command(command, args_list=args_list) == expected

        mocker.patch.object(obj.ctx, "no_color", True)
        expected.append("-no-color")
        assert obj.gen_command(command, args_list=args_list) == expected

    def test_handle_backend_no_handler(
        self,
        caplog: LogCaptureFixture,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test handle_backend with no handler."""
        caplog.set_level(LogLevels.DEBUG, logger=MODULE)
        mock_get_full_configuration = MagicMock(return_value={})
        backend: Dict[str, Union[Dict[str, Any], str]] = {
            "type": "unsupported",
            "config": {},
        }

        obj = Terraform(runway_context, module_root=tmp_path)
        mocker.patch.object(obj, "tfenv", MagicMock(backend=backend))
        mocker.patch.object(
            obj.options.backend_config,
            "get_full_configuration",
            mock_get_full_configuration,
        )
        assert not obj.handle_backend()
        mock_get_full_configuration.assert_not_called()
        assert 'backed "unsupported" does not require special handling' in "\n".join(
            caplog.messages
        )

    def test_handle_backend_no_type(
        self,
        caplog: LogCaptureFixture,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test handle_backend with no type."""
        caplog.set_level(LogLevels.INFO, logger=MODULE)
        obj = Terraform(runway_context, module_root=tmp_path)
        mocker.patch.object(obj, "tfenv", MagicMock(backend={"type": None}))
        assert not obj.handle_backend()
        assert "unable to determine backend for module" in "\n".join(caplog.messages)

    def test_handle_backend_remote_name(
        self,
        caplog: LogCaptureFixture,
        monkeypatch: MonkeyPatch,
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test handle_backend for remote backend with workspace prefix."""
        caplog.set_level(LogLevels.DEBUG, logger=MODULE)
        monkeypatch.setenv("TF_WORKSPACE", "anything")
        mock_get_full_configuration = MagicMock(return_value={})
        backend = {"type": "remote", "config": {"workspaces": {"name": "test"}}}

        obj = Terraform(runway_context, module_root=tmp_path)
        monkeypatch.setattr(obj, "tfenv", MagicMock(backend=backend))
        monkeypatch.setattr(
            obj.options.backend_config,
            "get_full_configuration",
            mock_get_full_configuration,
        )

        assert not obj.handle_backend()
        mock_get_full_configuration.assert_called_once_with()
        assert "TF_WORKSPACE" not in obj.ctx.env.vars
        assert obj.required_workspace == "default"
        assert 'forcing use of static workspace "default"' in "\n".join(caplog.messages)

    def test_handle_backend_remote_prefix(
        self,
        caplog: LogCaptureFixture,
        monkeypatch: MonkeyPatch,
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test handle_backend for remote backend with workspace prefix."""
        caplog.set_level(LogLevels.DEBUG, logger=MODULE)
        monkeypatch.delenv("TF_WORKSPACE", raising=False)
        mock_get_full_configuration = MagicMock(return_value={})
        backend = {"type": "remote", "config": {"workspaces": {"prefix": "test"}}}

        obj = Terraform(runway_context, module_root=tmp_path)
        monkeypatch.setattr(obj, "tfenv", MagicMock(backend=backend))
        monkeypatch.setattr(
            obj.options.backend_config,
            "get_full_configuration",
            mock_get_full_configuration,
        )

        assert not obj.handle_backend()
        mock_get_full_configuration.assert_called_once_with()
        assert obj.ctx.env.vars["TF_WORKSPACE"] == obj.ctx.env.name
        assert 'set environment variable "TF_WORKSPACE" to avoid prompt' in "\n".join(
            caplog.messages
        )

    def test_handle_backend_remote_undetermined(
        self,
        caplog: LogCaptureFixture,
        monkeypatch: MonkeyPatch,
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test handle_backend for remote backend with workspace undetermined."""
        caplog.set_level(LogLevels.WARNING, logger=MODULE)
        monkeypatch.delenv("TF_WORKSPACE", raising=False)
        mock_get_full_configuration = MagicMock(return_value={})
        backend: Dict[str, Union[Dict[str, Any], str]] = {
            "type": "remote",
            "config": {},
        }

        obj = Terraform(runway_context, module_root=tmp_path)
        monkeypatch.setattr(obj, "tfenv", MagicMock(backend=backend))
        monkeypatch.setattr(
            obj.options.backend_config,
            "get_full_configuration",
            mock_get_full_configuration,
        )

        assert not obj.handle_backend()
        mock_get_full_configuration.assert_called_once_with()
        assert '"workspaces" not defined in backend config' in "\n".join(
            caplog.messages
        )

    def test_handle_parameters(
        self, mocker: MockerFixture, runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test handle_parameters."""
        mock_update_envvars = mocker.patch(
            f"{MODULE}.update_env_vars_with_tf_var_values",
            return_value={"result": "success"},
        )
        obj = Terraform(runway_context.copy(), module_root=tmp_path)
        mocker.patch.object(
            obj, "auto_tfvars", MagicMock(exists=MagicMock(side_effect=[True, False]))
        )

        assert not obj.handle_parameters()
        mock_update_envvars.assert_not_called()

        assert not obj.handle_parameters()
        mock_update_envvars.assert_called_once_with(runway_context.env.vars, {})
        assert obj.ctx.env.vars == {"result": "success"}

    @pytest.mark.parametrize(
        "env, param, expected",
        [
            (False, False, True),
            (True, False, False),
            (False, True, False),
            (True, True, False),
        ],
    )
    def test_skip(
        self,
        env: bool,
        param: bool,
        expected: bool,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test skip."""
        mocker.patch.object(Terraform, "env_file", env)
        obj = Terraform(runway_context, module_root=tmp_path)
        obj.parameters = param  # type: ignore
        assert obj.skip == expected

    def test_tfenv(
        self, mocker: MockerFixture, runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test tfenv."""
        mock_tfenv = mocker.patch(f"{MODULE}.TFEnvManager", return_value="tfenv")
        obj = Terraform(runway_context, module_root=tmp_path)

        assert obj.tfenv == "tfenv"
        mock_tfenv.assert_called_once_with(tmp_path)

    def test_tf_bin_file(
        self, mocker: MockerFixture, runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test tf_bin version in file."""
        mock_tfenv = MagicMock(version_file=True)
        mock_tfenv.install.return_value = "success"
        mocker.patch.object(Terraform, "tfenv", mock_tfenv)
        obj = Terraform(runway_context, module_root=tmp_path)
        assert obj.tf_bin == "success"
        mock_tfenv.install.assert_called_once_with(None)

    def test_tf_bin_global(
        self, mocker: MockerFixture, runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test tf_bin from global install."""
        mocker.patch.object(
            Terraform, "tfenv", MagicMock(install=MagicMock(side_effect=ValueError))
        )
        mock_which = mocker.patch(f"{MODULE}.which", return_value=True)
        obj = Terraform(runway_context, module_root=tmp_path)
        assert obj.tf_bin == "terraform"
        mock_which.assert_called_once_with("terraform")

    def test_tf_bin_missing(
        self,
        caplog: LogCaptureFixture,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test tf_bin missing."""
        caplog.set_level(LogLevels.ERROR, logger=MODULE)
        mock_which = mocker.patch(f"{MODULE}.which", return_value=False)
        mocker.patch.object(
            Terraform, "tfenv", MagicMock(install=MagicMock(side_effect=ValueError))
        )
        obj = Terraform(runway_context, module_root=tmp_path)
        with pytest.raises(SystemExit) as excinfo:
            assert obj.tf_bin
        assert excinfo.value.code == 1
        mock_which.assert_called_once_with("terraform")
        assert (
            "terraform not available and a version to install not specified"
            in "\n".join(caplog.messages)
        )

    def test_tf_bin_options(
        self, mocker: MockerFixture, runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test tf_bin version in options."""
        mock_tfenv = MagicMock()
        mock_tfenv.install.return_value = "success"
        mocker.patch.object(Terraform, "tfenv", mock_tfenv)
        options = {"terraform_version": "0.12.0"}
        obj = Terraform(runway_context, module_root=tmp_path, options=options)
        assert obj.tf_bin == "success"
        mock_tfenv.install.assert_called_once_with("0.12.0")

    def test_terraform_apply(
        self, mocker: MockerFixture, runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test terraform_apply."""
        mock_gen_command = mocker.patch.object(Terraform, "gen_command")
        mock_run_command = mocker.patch(f"{MODULE}.run_module_command")
        mock_gen_command.return_value = ["mock_gen_command"]
        options = {"args": {"apply": ["arg"]}}
        obj = Terraform(runway_context, module_root=tmp_path, options=options)
        mocker.patch.object(obj, "env_file", ["env_file"])
        mocker.patch.object(obj.ctx.env, "ci", True)

        expected_arg_list = ["env_file", "arg", "-auto-approve=true"]
        assert not obj.terraform_apply()
        mock_gen_command.assert_called_once_with("apply", expected_arg_list)
        mock_run_command.assert_called_once_with(
            ["mock_gen_command"], env_vars=obj.ctx.env.vars, logger=obj.logger
        )

        mocker.patch.object(obj.ctx.env, "ci", False)
        expected_arg_list[2] = "-auto-approve=false"
        assert not obj.terraform_apply()
        mock_gen_command.assert_called_with("apply", expected_arg_list)
        assert mock_run_command.call_count == 2

    @pytest.mark.parametrize(
        "version, expected_subcmd, expected_options",
        [
            (Version("0.15.5"), "apply", ["-destroy", "-auto-approve"]),
            (Version("0.15.2"), "apply", ["-destroy", "-auto-approve"]),
            (Version("0.15.1"), "destroy", ["-auto-approve"]),
            (Version("0.13.3"), "destroy", ["-auto-approve"]),
            (Version("0.11.2"), "destroy", ["-force"]),
        ],
    )
    def test_terraform_destroy(
        self,
        expected_options: List[str],
        expected_subcmd: str,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        tmp_path: Path,
        version: Version,
    ) -> None:
        """Test terraform_destroy."""
        mock_gen_command = mocker.patch.object(
            Terraform, "gen_command", return_value=["mock_gen_command"]
        )
        mocker.patch.object(Terraform, "version", version)
        mock_run_command = mocker.patch(
            f"{MODULE}.run_module_command", return_value=None
        )
        obj = Terraform(runway_context, module_root=tmp_path)
        mocker.patch.object(obj, "env_file", ["env_file"])

        expected_options.append("env_file")
        assert not obj.terraform_destroy()
        mock_gen_command.assert_called_once_with(expected_subcmd, expected_options)
        mock_run_command.assert_called_once_with(
            ["mock_gen_command"], env_vars=obj.ctx.env.vars, logger=obj.logger
        )

    def test_terraform_get(
        self,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test terraform_get."""
        mock_gen_command = mocker.patch.object(
            Terraform, "gen_command", return_value=["mock_gen_command"]
        )
        mock_run_command = mocker.patch(f"{MODULE}.run_module_command")
        obj = Terraform(runway_context, module_root=tmp_path)

        assert not obj.terraform_get()
        mock_gen_command.assert_called_once_with("get", ["-update=true"])
        mock_run_command.assert_called_once_with(
            ["mock_gen_command"], env_vars=obj.ctx.env.vars, logger=obj.logger
        )

    def test_terraform_init(
        self, mocker: MockerFixture, runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test terraform_init."""
        mock_gen_command = mocker.patch.object(
            Terraform, "gen_command", return_value=["mock_gen_command"]
        )
        mock_run_command = mocker.patch(f"{MODULE}.run_module_command")
        options: Dict[str, Union[Dict[str, Any], str]] = {
            "args": {"init": ["init_arg"]},
            "terraform_backend_config": {"bucket": "name"},
        }
        obj = Terraform(runway_context, module_root=tmp_path, options=options)

        expected_arg_list = [
            "-reconfigure",
            "-backend-config",
            "bucket=name",
            "-backend-config",
            "region=us-east-1",
            "init_arg",
        ]
        assert not obj.terraform_init()
        mock_gen_command.assert_called_once_with("init", expected_arg_list)
        mock_run_command.assert_called_once_with(
            ["mock_gen_command"],
            env_vars=obj.ctx.env.vars,
            exit_on_error=False,
            logger=obj.logger,
        )

        mock_run_command.side_effect = subprocess.CalledProcessError(1, "")
        with pytest.raises(SystemExit) as excinfo:
            assert obj.terraform_init()
        assert excinfo.value.code == 1

    def test_terraform_plan(
        self, mocker: MockerFixture, runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test terraform_plan."""
        mock_gen_command = mocker.patch.object(
            Terraform, "gen_command", return_value=["mock_gen_command"]
        )
        mock_run_command = mocker.patch(f"{MODULE}.run_module_command")
        options = {"args": {"plan": ["plan_arg"]}}
        obj = Terraform(runway_context, module_root=tmp_path, options=options)
        mocker.patch.object(obj, "env_file", ["env_file"])

        assert not obj.terraform_plan()
        mock_gen_command.assert_called_once_with("plan", ["env_file", "plan_arg"])
        mock_run_command.assert_called_once_with(
            ["mock_gen_command"], env_vars=obj.ctx.env.vars, logger=obj.logger
        )

    def test_terraform_workspace_list(
        self, mocker: MockerFixture, runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test terraform_workspace_list."""
        mock_gen_command = mocker.patch.object(
            Terraform, "gen_command", return_value=["mock_gen_command"]
        )
        mock_subprocess = mocker.patch(f"{MODULE}.subprocess")
        check_output_result = MagicMock()
        check_output_result.decode.return_value = "decoded"
        mock_subprocess.check_output.return_value = check_output_result

        obj = Terraform(runway_context, module_root=tmp_path)
        assert obj.terraform_workspace_list() == "decoded"
        mock_gen_command.assert_called_once_with(["workspace", "list"])
        mock_subprocess.check_output.assert_called_once_with(
            ["mock_gen_command"], env=obj.ctx.env.vars
        )
        check_output_result.decode.assert_called_once_with()

    def test_terraform_workspace_new(
        self, mocker: MockerFixture, runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test terraform_workspace_new."""
        mock_gen_command = mocker.patch.object(
            Terraform, "gen_command", return_value=["mock_gen_command"]
        )
        mock_run_command = mocker.patch(f"{MODULE}.run_module_command")
        obj = Terraform(runway_context, module_root=tmp_path)

        assert not obj.terraform_workspace_new("name")
        mock_gen_command.assert_called_once_with(["workspace", "new"], ["name"])
        mock_run_command.assert_called_once_with(
            ["mock_gen_command"], env_vars=obj.ctx.env.vars, logger=obj.logger
        )

    def test_terraform_workspace_select(
        self, mocker: MockerFixture, runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test terraform_workspace_new."""
        mock_gen_command = mocker.patch.object(
            Terraform, "gen_command", return_value=["mock_gen_command"]
        )
        mock_run_command = mocker.patch(f"{MODULE}.run_module_command")
        mocker.patch.object(
            Terraform,
            "terraform_workspace_show",
            side_effect=["first-val", "second-val"],
        )
        obj = Terraform(runway_context, module_root=tmp_path)

        assert obj.current_workspace == "first-val"  # load cached value
        assert not obj.terraform_workspace_select("name")
        mock_gen_command.assert_called_once_with(["workspace", "select"], ["name"])
        mock_run_command.assert_called_once_with(
            ["mock_gen_command"], env_vars=obj.ctx.env.vars, logger=obj.logger
        )
        # cache was cleared and a new value was obtained
        assert obj.current_workspace == "second-val"

    def test_terraform_workspace_show(
        self, mocker: MockerFixture, runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test terraform_workspace_show."""
        mock_gen_command = mocker.patch.object(
            Terraform, "gen_command", return_value=["mock_gen_command"]
        )
        mock_subprocess = mocker.patch(f"{MODULE}.subprocess")
        check_output_result = MagicMock(
            strip=MagicMock(
                return_value=MagicMock(decode=MagicMock(return_value="decoded"))
            )
        )
        mock_subprocess.check_output.return_value = check_output_result

        obj = Terraform(runway_context, module_root=tmp_path)
        assert obj.terraform_workspace_show() == "decoded"
        mock_gen_command.assert_called_once_with(["workspace", "show"])
        mock_subprocess.check_output.assert_called_once_with(
            ["mock_gen_command"], env=obj.ctx.env.vars
        )
        check_output_result.strip.assert_called_once_with()
        check_output_result.strip.return_value.decode.assert_called_once_with()

    def test_version(
        self, mocker: MockerFixture, runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test version."""
        version = Version("0.15.5")
        tfenv = Mock(current_version="0.15.5", version=version)
        mocker.patch.object(Terraform, "tfenv", tfenv)
        assert Terraform(runway_context, module_root=tmp_path).version == version

    def test_version_from_executable(
        self, mocker: MockerFixture, runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test version from executable."""
        version = Version("0.15.5")
        tfenv = Mock(current_version=None, version=None)
        tfenv.get_version_from_executable.return_value = version
        mocker.patch.object(Terraform, "tfenv", tfenv)
        mocker.patch.object(Terraform, "tf_bin", "/bin/terraform")
        obj = Terraform(runway_context, module_root=tmp_path)
        assert obj.version == version
        tfenv.get_version_from_executable.assert_called_once_with(obj.tf_bin)

    def test_version_from_options(
        self, mocker: MockerFixture, runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test version from options."""
        version = Version("0.15.5")
        tfenv = Mock(current_version=None, version=version)
        mocker.patch.object(Terraform, "tfenv", tfenv)
        assert (
            Terraform(
                runway_context,
                module_root=tmp_path,
                options={"terraform_version": "0.15.5"},
            ).version
            == version
        )
        tfenv.set_version.assert_called_once_with("0.15.5")

    def test_version_raise_value_error(
        self, mocker: MockerFixture, runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test version."""
        tfenv = Mock(current_version=None, version=None)
        tfenv.get_version_from_executable.return_value = None
        mocker.patch.object(Terraform, "tfenv", tfenv)
        mocker.patch.object(Terraform, "tf_bin", "/bin/terraform")
        with pytest.raises(
            ValueError, match="unable to retrieve version from /bin/terraform"
        ):
            assert Terraform(runway_context, module_root=tmp_path).version


class TestTerraformOptions:
    """Test runway.module.terraform.TerraformOptions."""

    def test_backend_config(
        self, mocker: MockerFixture, runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test backend_config."""
        backend_config = {"bucket": "test"}
        mocker.patch.object(TerraformBackendConfig, "parse_obj", return_value="success")
        obj = TerraformOptions.parse_obj(
            deploy_environment=runway_context.env,
            obj={"terraform_backend_config": backend_config},
            path=tmp_path,
        )
        assert obj.backend_config == "success"

    @pytest.mark.parametrize(
        "config",
        [
            ({"args": ["-key=val"]}),
            ({"args": {"apply": ["-key=apply"]}}),
            ({"args": {"init": ["-key=init"]}}),
            ({"args": {"plan": ["-key=plan"]}}),
            ({"args": {"apply": ["-key=apply"], "init": ["-key=init"]}}),
            (
                {
                    "args": {
                        "apply": ["-key=apply"],
                        "init": ["-key=init"],
                        "plan": ["-key=plan"],
                    }
                }
            ),
            (
                {
                    "terraform_backend_config": {
                        "bucket": "foo",
                        "dynamodb_table": "bar",
                        "region": "us-west-2",
                    }
                }
            ),
            (
                {
                    "terraform_backend_config": {
                        "bucket": "foo",
                        "dynamodb_table": "bar",
                        "region": "us-west-2",
                        "workspace_key_prefix": "foobar",
                    }
                }
            ),
            (
                {
                    "terraform_backend_config": {"region": "us-west-2"},
                    "terraform_backend_cfn_outputs": {
                        "bucket": "foo",
                        "dynamodb_table": "bar",
                    },
                }
            ),
            (
                {
                    "terraform_backend_config": {"region": "us-west-2"},
                    "terraform_backend_ssm_params": {
                        "bucket": "foo",
                        "dynamodb_table": "bar",
                    },
                }
            ),
            ({"terraform_version": "0.11.6"}),
            (
                {
                    "args": {
                        "apply": ["-key=apply"],
                        "init": ["-key=init"],
                        "plan": ["-key=plan"],
                    },
                    "terraform_backend_config": {
                        "bucket": "foo",
                        "dynamodb_table": "bar",
                        "region": "us-west-2",
                    },
                    "terraform_version": "0.11.6",
                }
            ),
        ],
    )
    def test_parse_obj(
        self, config: Dict[str, Any], runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test parse_obj."""
        obj = TerraformOptions.parse_obj(
            deploy_environment=runway_context.env, obj=config, path=tmp_path
        )

        if isinstance(config.get("args"), list):
            assert obj.args.apply == config["args"]
            assert obj.args.init == []
            assert obj.args.plan == []
        elif isinstance(config.get("args"), dict):
            assert obj.args.apply == config["args"].get("apply", [])
            assert obj.args.init == config["args"].get("init", [])
            assert obj.args.plan == config["args"].get("plan", [])
        assert obj.version == config.get("terraform_version")


class TestTerraformBackendConfig:
    """Test runway.module.terraform.TerraformBackendConfig."""

    def test_get_full_configuration(
        self, runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test get_full_configuration."""
        config_file = tmp_path / "backend.hcl"
        config_file.write_text('dynamodb_table = "test-table"')
        backend = TerraformBackendConfig.parse_obj(
            deploy_environment=runway_context.env, obj={"bucket": "test-bucket"}
        )
        assert backend.get_full_configuration() == {
            "bucket": "test-bucket",
            "region": "us-east-1",
        }
        backend.config_file = config_file  # type: ignore
        assert backend.get_full_configuration() == {
            "bucket": "test-bucket",
            "dynamodb_table": "test-table",
            "region": "us-east-1",
        }

    @pytest.mark.parametrize(
        "input_data, expected_items",
        [
            ({}, []),
            (
                {"dynamodb_table": "test-table"},
                ["dynamodb_table=test-table", "region=us-east-1"],
            ),
            ({"region": "us-east-1"}, ["region=us-east-1"]),
            (
                {"bucket": "test-bucket", "dynamodb_table": "test-table"},
                ["bucket=test-bucket", "dynamodb_table=test-table", "region=us-east-1"],
            ),
            (
                {
                    "bucket": "test-bucket",
                    "dynamodb_table": "test-table",
                    "region": "us-east-1",
                },
                ["bucket=test-bucket", "dynamodb_table=test-table", "region=us-east-1"],
            ),
            (
                {
                    "bucket": "test-bucket",
                    "dynamodb_table": "test-table",
                    "region": "us-east-1",
                },
                ["bucket=test-bucket", "dynamodb_table=test-table", "region=us-east-1"],
            ),
        ],
    )
    def test_init_args(
        self,
        expected_items: List[str],
        input_data: Dict[str, str],
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test init_args."""
        expected: List[str] = []
        for i in expected_items:
            expected.extend(["-backend-config", i])
        assert (
            TerraformBackendConfig.parse_obj(
                deploy_environment=runway_context.env, obj=input_data, path=tmp_path
            ).init_args
            == expected
        )

    def test_init_args_file(
        self,
        caplog: LogCaptureFixture,
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test init_args with backend file."""
        caplog.set_level(LogLevels.VERBOSE, logger=MODULE)
        config_file = tmp_path / "backend.hcl"
        config_file.touch()
        obj = TerraformBackendConfig.parse_obj(
            deploy_environment=runway_context.env, obj={}, path=tmp_path
        )
        assert obj.init_args == [f"-backend-config={config_file.name}"]
        assert "using backend config file: backend.hcl" in caplog.messages

    def test_gen_backend_filenames(self) -> None:
        """Test gen_backend_filenames."""
        expected = [
            "backend-test-us-east-1.hcl",
            "backend-test-us-east-1.tfvars",
            "backend-test.hcl",
            "backend-test.tfvars",
            "backend-us-east-1.hcl",
            "backend-us-east-1.tfvars",
            "backend.hcl",
            "backend.tfvars",
        ]

        assert (
            TerraformBackendConfig.gen_backend_filenames("test", "us-east-1")
            == expected
        )

    @pytest.mark.parametrize(
        "filename, expected",
        [
            ("backend-test-us-east-1.tfvars", "backend-test-us-east-1.tfvars"),
            ("backend-test.tfvars", "backend-test.tfvars"),
            ("backend-us-east-1.tfvars", "backend-us-east-1.tfvars"),
            ("backend.tfvars", "backend.tfvars"),
            ("something-backend.tfvars", None),
            (
                ["backend-test-us-east-1.tfvars", "backend.tfvars"],
                "backend-test-us-east-1.tfvars",
            ),
        ],
    )
    def test_get_backend_file(
        self, tmp_path: Path, filename: Union[List[str], str], expected: Optional[str]
    ) -> None:
        """Test get_backend_file."""
        if isinstance(filename, list):
            for name in filename:
                (tmp_path / name).touch()
        else:
            (tmp_path / filename).touch()
        result = TerraformBackendConfig.get_backend_file(tmp_path, "test", "us-east-1")
        if expected:
            assert result == tmp_path / expected
        else:
            assert not result

    @pytest.mark.parametrize(
        "config, expected_region",
        [
            (
                {"bucket": "foo", "dynamodb_table": "bar", "region": "us-west-2"},
                "us-west-2",
            ),
            ({"bucket": "foo", "dynamodb_table": "bar"}, "us-east-1"),
        ],
    )
    def test_parse_obj(
        self,
        config: Dict[str, str],
        expected_region: str,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test parse_obj."""

        def assert_get_backend_file_args(
            _cls: Type[TerraformBackendConfig],
            path: Path,
            env_name: str,
            env_region: str,
        ):
            """Assert args passed to the method during parse."""
            assert path == tmp_path
            assert env_name == "test"
            assert env_region == "us-east-1"
            return "success"

        mocker.patch.object(
            TerraformBackendConfig, "get_backend_file", assert_get_backend_file_args
        )

        result = TerraformBackendConfig.parse_obj(
            deploy_environment=runway_context.env, obj=config, path=tmp_path
        )

        assert result.bucket == "foo"
        assert result.dynamodb_table == "bar"
        assert result.region == expected_region
        assert result.config_file == "success"
