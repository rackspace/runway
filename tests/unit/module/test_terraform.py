"""Test runway.module.terraform."""
# pylint: disable=no-self-use,protected-access,too-many-statements,unused-argument
import json
import logging
import subprocess
import sys
from contextlib import contextmanager
from datetime import datetime

import boto3
import pytest
import six
from botocore.stub import Stubber
from mock import MagicMock, patch

from runway._logging import LogLevels
from runway.module.terraform import (
    Terraform,
    TerraformBackendConfig,
    TerraformOptions,
    gen_workspace_tfvars_files,
    update_env_vars_with_tf_var_values,
)

MODULE = "runway.module.terraform"


@contextmanager
def does_not_raise():
    """Use for conditional pytest.raises when using parametrize."""
    yield


def test_gen_workspace_tfvars_files():
    """Test gen_workspace_tfvars_files."""
    assert gen_workspace_tfvars_files("test", "us-east-1") == [
        "test-us-east-1.tfvars",
        "test.tfvars",
    ]


def test_update_env_vars_with_tf_var_values():
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

    assert sorted(result) == sorted(expected)  # sorted() needed for python 2


class TestTerraform(object):  # pylint: disable=too-many-public-methods
    """Test runway.module.terraform.Terraform."""

    def test_auto_tfvars(self, caplog, monkeypatch, runway_context, tmp_path):
        """Test auto_tfvars."""
        caplog.set_level(LogLevels.DEBUG, logger=MODULE)
        mock_tfenv = MagicMock(current_version="0.12.0")
        monkeypatch.setattr(Terraform, "tfenv", mock_tfenv)
        options = {
            "options": {"terraform_write_auto_tfvars": True},
            "parameters": {"key": "val"},
        }
        obj = Terraform(runway_context, tmp_path, options=options.copy())
        assert obj.auto_tfvars.is_file()
        assert json.loads(obj.auto_tfvars.read_text()) == options["parameters"]
        assert "unable to parse current version" not in "\n".join(caplog.messages)

        # check cases where the file will not be written
        obj.auto_tfvars.unlink()
        del obj.auto_tfvars
        obj.options.write_auto_tfvars = False
        assert not obj.auto_tfvars.exists()

        del obj.auto_tfvars
        obj.options.write_auto_tfvars = True
        obj.parameters = {}
        assert not obj.auto_tfvars.exists()

    def test_auto_tfvars_invalid_version(
        self, caplog, monkeypatch, runway_context, tmp_path
    ):
        """Test auto_tfvars with a version that cannot be converted to int."""
        caplog.set_level(LogLevels.DEBUG, logger=MODULE)
        mock_tfenv = MagicMock(current_version="v0.12.0")
        monkeypatch.setattr(Terraform, "tfenv", mock_tfenv)
        options = {
            "options": {"terraform_write_auto_tfvars": True},
            "parameters": {"key": "val"},
        }
        obj = Terraform(runway_context, tmp_path, options=options.copy())
        assert obj.auto_tfvars.is_file()
        assert json.loads(obj.auto_tfvars.read_text()) == options["parameters"]
        assert "unable to parse current version" in "\n".join(caplog.messages)

    def test_auto_tfvars_unsupported_version(
        self, caplog, monkeypatch, runway_context, tmp_path
    ):
        """Test auto_tfvars with a version that does not support it."""
        caplog.set_level(LogLevels.WARNING, logger=MODULE)
        mock_tfenv = MagicMock(current_version="0.9.0")
        monkeypatch.setattr(Terraform, "tfenv", mock_tfenv)
        options = {
            "options": {"terraform_write_auto_tfvars": True},
            "parameters": {"key": "val"},
        }
        obj = Terraform(runway_context, tmp_path, options=options.copy())
        assert obj.auto_tfvars.is_file()
        assert json.loads(obj.auto_tfvars.read_text()) == options["parameters"]
        assert (
            "Terraform version does not support the use of "
            "*.auto.tfvars; some variables may be missing"
        ) in "\n".join(caplog.messages)

    @patch.object(Terraform, "terraform_workspace_show")
    def test_current_workspace(
        self, mock_terraform_workspace_show, runway_context, tmp_path
    ):
        """Test current_workspace."""
        mock_terraform_workspace_show.return_value = "default"
        assert Terraform(runway_context, tmp_path).current_workspace == "default"
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
    def test_env_file(self, filename, expected, runway_context, tmp_path):
        """Test env_file."""
        obj = Terraform(runway_context, tmp_path)

        if isinstance(filename, list):
            for name in filename:
                (tmp_path / name).touch()
        else:
            (tmp_path / filename).touch()
        if expected:
            assert obj.env_file == ["-var-file=" + expected]
        else:
            assert not obj.env_file

    def test_init(self, runway_context, tmp_path):
        """Test class instantiation."""
        options = {
            "environments": {"test": "something"},
            "parameters": {"key1": "val1"},
            "nonstandard_key": "something",
        }
        obj = Terraform(runway_context, tmp_path, options=options.copy())

        assert obj.logger
        assert obj.path == tmp_path
        assert obj.environments == options["environments"]
        assert isinstance(obj.options, TerraformOptions)
        assert obj.parameters == options["parameters"]
        assert obj.required_workspace == runway_context.env.name

        assert (
            obj.nonstandard_key  # pylint: disable=no-member
            == options["nonstandard_key"]
        )

    def test_init_options_workspace(self, runway_context, tmp_path):
        """Test class instantiation with workspace option."""
        options = {"options": {"terraform_workspace": "default"}}
        obj = Terraform(runway_context, tmp_path, options=options.copy())
        assert obj.required_workspace == options["options"]["terraform_workspace"]

    @pytest.mark.parametrize(
        "env, param, expected",
        [
            (False, False, True),
            (True, False, False),
            (False, True, False),
            (True, True, False),
        ],
    )
    def test_skip(self, env, param, expected, monkeypatch, runway_context, tmp_path):
        """Test skip."""
        monkeypatch.setattr(Terraform, "env_file", env)
        obj = Terraform(runway_context, tmp_path)
        obj.parameters = param
        assert obj.skip == expected

    @patch(MODULE + ".TFEnvManager")
    def test_tfenv(self, mock_tfenv, runway_context, tmp_path):
        """Test tfenv."""
        mock_tfenv.return_value = "tfenv"
        obj = Terraform(runway_context, tmp_path)

        assert obj.tfenv == "tfenv"
        mock_tfenv.assert_called_once_with(tmp_path)

    def test_tf_bin_file(self, monkeypatch, runway_context, tmp_path):
        """Test tf_bin version in file."""
        mock_tfenv = MagicMock(version_file=True)
        mock_tfenv.install.return_value = "success"
        monkeypatch.setattr(Terraform, "tfenv", mock_tfenv)
        obj = Terraform(runway_context, tmp_path)
        assert obj.tf_bin == "success"
        mock_tfenv.install.assert_called_once_with(None)

    @patch(MODULE + ".which")
    def test_tf_bin_global(self, mock_which, monkeypatch, runway_context, tmp_path):
        """Test tf_bin from global install."""
        mock_tfenv = MagicMock(install=MagicMock(side_effect=ValueError))
        monkeypatch.setattr(Terraform, "tfenv", mock_tfenv)
        mock_which.return_value = True
        obj = Terraform(runway_context, tmp_path)
        assert obj.tf_bin == "terraform"
        mock_which.assert_called_once_with("terraform")

    @patch(MODULE + ".which")
    def test_tf_bin_missing(
        self, mock_which, caplog, monkeypatch, runway_context, tmp_path
    ):
        """Test tf_bin missing."""
        caplog.set_level(LogLevels.ERROR, logger=MODULE)
        mock_tfenv = MagicMock(install=MagicMock(side_effect=ValueError))
        monkeypatch.setattr(Terraform, "tfenv", mock_tfenv)
        mock_which.return_value = False
        obj = Terraform(runway_context, tmp_path)
        with pytest.raises(SystemExit) as excinfo:
            assert obj.tf_bin
        assert excinfo.value.code == 1
        mock_which.assert_called_once_with("terraform")
        assert (
            "terraform not available and a version to install not specified"
            in "\n".join(caplog.messages)
        )

    def test_tf_bin_options(self, monkeypatch, runway_context, tmp_path):
        """Test tf_bin version in options."""
        mock_tfenv = MagicMock()
        mock_tfenv.install.return_value = "success"
        monkeypatch.setattr(Terraform, "tfenv", mock_tfenv)
        options = {"options": {"terraform_version": "0.12.0"}}
        obj = Terraform(runway_context, tmp_path, options=options)
        assert obj.tf_bin == "success"
        mock_tfenv.install.assert_called_once_with("0.12.0")

    def test_cleanup_dot_terraform(self, caplog, runway_context, tmp_path):
        """Test cleanup_dot_terraform."""
        caplog.set_level(logging.DEBUG, logger=MODULE)
        obj = Terraform(runway_context, tmp_path)

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
        self, command, args_list, expected, monkeypatch, runway_context, tmp_path
    ):
        """Test gen_command."""
        monkeypatch.setattr(Terraform, "tf_bin", "terraform")
        expected.insert(0, "terraform")

        obj = Terraform(runway_context, tmp_path)
        monkeypatch.setattr(obj.context, "no_color", False)
        assert obj.gen_command(command, args_list=args_list) == expected

        monkeypatch.setattr(obj.context, "no_color", True)
        expected.append("-no-color")
        assert obj.gen_command(command, args_list=args_list) == expected

    def test_handle_backend_no_handler(
        self, caplog, monkeypatch, runway_context, tmp_path
    ):
        """Test handle_backend with no handler."""
        caplog.set_level(LogLevels.DEBUG, logger=MODULE)
        mock_get_full_configuration = MagicMock(return_value={})
        backend = {"type": "unsupported", "config": {}}

        obj = Terraform(runway_context, tmp_path)
        monkeypatch.setattr(obj, "tfenv", MagicMock(backend=backend))
        monkeypatch.setattr(
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
        self, caplog, monkeypatch, runway_context, tmp_path
    ):
        """Test handle_backend with no type."""
        caplog.set_level(LogLevels.INFO, logger=MODULE)
        obj = Terraform(runway_context, tmp_path)
        monkeypatch.setattr(obj, "tfenv", MagicMock(backend={"type": None}))
        assert not obj.handle_backend()
        assert "unable to determine backend for module" in "\n".join(caplog.messages)

    def test_handle_backend_remote_name(
        self, caplog, monkeypatch, runway_context, tmp_path
    ):
        """Test handle_backend for remote backend with workspace prefix."""
        caplog.set_level(LogLevels.DEBUG, logger=MODULE)
        monkeypatch.setenv("TF_WORKSPACE", "anything")
        mock_get_full_configuration = MagicMock(return_value={})
        backend = {"type": "remote", "config": {"workspaces": {"name": "test"}}}

        obj = Terraform(runway_context, tmp_path)
        monkeypatch.setattr(obj, "tfenv", MagicMock(backend=backend))
        monkeypatch.setattr(
            obj.options.backend_config,
            "get_full_configuration",
            mock_get_full_configuration,
        )

        assert not obj.handle_backend()
        mock_get_full_configuration.assert_called_once_with()
        assert "TF_WORKSPACE" not in obj.context.env.vars
        assert obj.required_workspace == "default"
        assert 'forcing use of static workspace "default"' in "\n".join(caplog.messages)

    def test_handle_backend_remote_prefix(
        self, caplog, monkeypatch, runway_context, tmp_path
    ):
        """Test handle_backend for remote backend with workspace prefix."""
        caplog.set_level(LogLevels.DEBUG, logger=MODULE)
        monkeypatch.delenv("TF_WORKSPACE", raising=False)
        mock_get_full_configuration = MagicMock(return_value={})
        backend = {"type": "remote", "config": {"workspaces": {"prefix": "test"}}}

        obj = Terraform(runway_context, tmp_path)
        monkeypatch.setattr(obj, "tfenv", MagicMock(backend=backend))
        monkeypatch.setattr(
            obj.options.backend_config,
            "get_full_configuration",
            mock_get_full_configuration,
        )

        assert not obj.handle_backend()
        mock_get_full_configuration.assert_called_once_with()
        assert obj.context.env.vars["TF_WORKSPACE"] == obj.context.env.name
        assert 'set environment variable "TF_WORKSPACE" to avoid prompt' in "\n".join(
            caplog.messages
        )

    def test_handle_backend_remote_undetermined(
        self, caplog, monkeypatch, runway_context, tmp_path
    ):
        """Test handle_backend for remote backend with workspace undetermined."""
        caplog.set_level(LogLevels.WARNING, logger=MODULE)
        monkeypatch.delenv("TF_WORKSPACE", raising=False)
        mock_get_full_configuration = MagicMock(return_value={})
        backend = {"type": "remote", "config": {}}

        obj = Terraform(runway_context, tmp_path)
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

    @patch(MODULE + ".update_env_vars_with_tf_var_values")
    def test_handle_parameters(
        self, mock_update_envvars, monkeypatch, runway_context, tmp_path
    ):
        """Test handle_parameters."""
        mock_update_envvars.return_value = {"result": "success"}
        obj = Terraform(runway_context, tmp_path)
        monkeypatch.setattr(
            obj, "auto_tfvars", MagicMock(exists=MagicMock(side_effect=[True, False]))
        )

        assert not obj.handle_parameters()
        mock_update_envvars.assert_not_called()

        assert not obj.handle_parameters()
        mock_update_envvars.assert_called_once_with(runway_context.env.vars, {})
        assert obj.context.env.vars == {"result": "success"}

    @patch(MODULE + ".run_module_command")
    @patch.object(Terraform, "gen_command")
    def test_terraform_apply(
        self, mock_gen_command, mock_run_command, monkeypatch, runway_context, tmp_path
    ):
        """Test terraform_apply."""
        mock_gen_command.return_value = ["mock_gen_command"]
        options = {"options": {"args": {"apply": ["arg"]}}}
        obj = Terraform(runway_context, tmp_path, options=options)
        monkeypatch.setattr(obj, "env_file", ["env_file"])
        monkeypatch.setattr(obj.context.env, "ci", True)

        expected_arg_list = ["env_file", "arg", "-auto-approve=true"]
        assert not obj.terraform_apply()
        mock_gen_command.assert_called_once_with("apply", expected_arg_list)
        mock_run_command.assert_called_once_with(
            ["mock_gen_command"], env_vars=obj.context.env.vars, logger=obj.logger
        )

        monkeypatch.setattr(obj.context.env, "ci", False)
        expected_arg_list[2] = "-auto-approve=false"
        assert not obj.terraform_apply()
        mock_gen_command.assert_called_with("apply", expected_arg_list)
        assert mock_run_command.call_count == 2

    @patch(MODULE + ".run_module_command")
    @patch.object(Terraform, "gen_command")
    def test_terraform_destroy(
        self, mock_gen_command, mock_run_command, monkeypatch, runway_context, tmp_path
    ):
        """Test terraform_destroy."""
        mock_gen_command.return_value = ["mock_gen_command"]
        obj = Terraform(runway_context, tmp_path)
        monkeypatch.setattr(obj, "env_file", ["env_file"])

        expected_arg_list = ["-force", "env_file"]
        assert not obj.terraform_destroy()
        mock_gen_command.assert_called_once_with("destroy", expected_arg_list)
        mock_run_command.assert_called_once_with(
            ["mock_gen_command"], env_vars=obj.context.env.vars, logger=obj.logger
        )

    @patch(MODULE + ".run_module_command")
    @patch.object(Terraform, "gen_command")
    def test_terraform_get(
        self, mock_gen_command, mock_run_command, runway_context, tmp_path
    ):
        """Test terraform_get."""
        mock_gen_command.return_value = ["mock_gen_command"]
        obj = Terraform(runway_context, tmp_path)

        assert not obj.terraform_get()
        mock_gen_command.assert_called_once_with("get", ["-update=true"])
        mock_run_command.assert_called_once_with(
            ["mock_gen_command"], env_vars=obj.context.env.vars, logger=obj.logger
        )

    @patch(MODULE + ".run_module_command")
    @patch.object(Terraform, "gen_command")
    def test_terraform_init(
        self, mock_gen_command, mock_run_command, runway_context, tmp_path
    ):
        """Test terraform_init."""
        mock_gen_command.return_value = ["mock_gen_command"]
        options = {
            "options": {
                "args": {"init": ["init_arg"]},
                "terraform_backend_config": {"bucket": "name"},
            }
        }
        obj = Terraform(runway_context, tmp_path, options=options)

        expected_arg_list = [
            "-reconfigure",
            "-backend-config",
            "bucket=name",
            "init_arg",
        ]
        assert not obj.terraform_init()
        mock_gen_command.assert_called_once_with("init", expected_arg_list)
        mock_run_command.assert_called_once_with(
            ["mock_gen_command"],
            env_vars=obj.context.env.vars,
            exit_on_error=False,
            logger=obj.logger,
        )

        mock_run_command.side_effect = subprocess.CalledProcessError(1, "")
        with pytest.raises(SystemExit) as excinfo:
            assert obj.terraform_init()
        assert excinfo.value.code == 1

    @patch(MODULE + ".run_module_command")
    @patch.object(Terraform, "gen_command")
    def test_terraform_plan(
        self, mock_gen_command, mock_run_command, monkeypatch, runway_context, tmp_path
    ):
        """Test terraform_plan."""
        mock_gen_command.return_value = ["mock_gen_command"]
        options = {"options": {"args": {"plan": ["plan_arg"]}}}
        obj = Terraform(runway_context, tmp_path, options=options)
        monkeypatch.setattr(obj, "env_file", ["env_file"])

        assert not obj.terraform_plan()
        mock_gen_command.assert_called_once_with("plan", ["env_file", "plan_arg"])
        mock_run_command.assert_called_once_with(
            ["mock_gen_command"], env_vars=obj.context.env.vars, logger=obj.logger
        )

    @patch(MODULE + ".subprocess")
    @patch.object(Terraform, "gen_command")
    def test_terraform_workspace_list(
        self, mock_gen_command, mock_subprocess, runway_context, tmp_path
    ):
        """Test terraform_workspace_list."""
        mock_gen_command.return_value = ["mock_gen_command"]
        check_output_result = MagicMock()
        check_output_result.decode.return_value = "decoded"
        mock_subprocess.check_output.return_value = check_output_result

        obj = Terraform(runway_context, tmp_path)
        assert obj.terraform_workspace_list() == "decoded"
        mock_gen_command.assert_called_once_with(["workspace", "list"])
        mock_subprocess.check_output.assert_called_once_with(
            ["mock_gen_command"], env=obj.context.env.vars
        )
        check_output_result.decode.assert_called_once_with()

    @patch(MODULE + ".run_module_command")
    @patch.object(Terraform, "gen_command")
    def test_terraform_workspace_new(
        self, mock_gen_command, mock_run_command, runway_context, tmp_path
    ):
        """Test terraform_workspace_new."""
        mock_gen_command.return_value = ["mock_gen_command"]
        obj = Terraform(runway_context, tmp_path)

        assert not obj.terraform_workspace_new("name")
        mock_gen_command.assert_called_once_with(["workspace", "new"], ["name"])
        mock_run_command.assert_called_once_with(
            ["mock_gen_command"], env_vars=obj.context.env.vars, logger=obj.logger
        )

    @patch(MODULE + ".run_module_command")
    @patch.object(Terraform, "terraform_workspace_show")
    @patch.object(Terraform, "gen_command")
    def test_terraform_workspace_select(
        self, mock_gen_command, mock_show, mock_run_command, runway_context, tmp_path
    ):
        """Test terraform_workspace_new."""
        mock_gen_command.return_value = ["mock_gen_command"]
        mock_show.side_effect = ["first-val", "second-val"]
        obj = Terraform(runway_context, tmp_path)

        assert obj.current_workspace == "first-val"  # load cached value
        assert not obj.terraform_workspace_select("name")
        mock_gen_command.assert_called_once_with(["workspace", "select"], ["name"])
        mock_run_command.assert_called_once_with(
            ["mock_gen_command"], env_vars=obj.context.env.vars, logger=obj.logger
        )
        # cache was cleared and a new value was obtained
        assert obj.current_workspace == "second-val"

    @patch(MODULE + ".subprocess")
    @patch.object(Terraform, "gen_command")
    def test_terraform_workspace_show(
        self, mock_gen_command, mock_subprocess, runway_context, tmp_path
    ):
        """Test terraform_workspace_show."""
        mock_gen_command.return_value = ["mock_gen_command"]
        check_output_result = MagicMock(
            strip=MagicMock(
                return_value=MagicMock(decode=MagicMock(return_value="decoded"))
            )
        )
        mock_subprocess.check_output.return_value = check_output_result

        obj = Terraform(runway_context, tmp_path)
        assert obj.terraform_workspace_show() == "decoded"
        mock_gen_command.assert_called_once_with(["workspace", "show"])
        mock_subprocess.check_output.assert_called_once_with(
            ["mock_gen_command"], env=obj.context.env.vars
        )
        check_output_result.strip.assert_called_once_with()
        check_output_result.strip.return_value.decode.assert_called_once_with()

    @pytest.mark.parametrize("action", ["deploy", "destroy", "plan"])
    def test_execute(self, action, caplog, monkeypatch, runway_context, tmp_path):
        """Test executing a Runway action."""
        caplog.set_level(LogLevels.DEBUG, logger=MODULE)
        monkeypatch.setattr(Terraform, "handle_backend", MagicMock())
        monkeypatch.setattr(Terraform, "skip", True)
        monkeypatch.setattr(Terraform, "cleanup_dot_terraform", MagicMock())
        monkeypatch.setattr(Terraform, "handle_parameters", MagicMock())
        monkeypatch.setattr(Terraform, "terraform_init", MagicMock())
        monkeypatch.setattr(Terraform, "current_workspace", "test")
        monkeypatch.setattr(
            Terraform, "terraform_workspace_list", MagicMock(return_value="* test")
        )
        monkeypatch.setattr(Terraform, "terraform_workspace_select", MagicMock())
        monkeypatch.setattr(Terraform, "terraform_workspace_new", MagicMock())
        monkeypatch.setattr(Terraform, "terraform_get", MagicMock())
        monkeypatch.setattr(Terraform, "terraform_apply", MagicMock())
        monkeypatch.setattr(Terraform, "terraform_destroy", MagicMock())
        monkeypatch.setattr(Terraform, "terraform_plan", MagicMock())
        monkeypatch.setattr(
            Terraform,
            "auto_tfvars",
            MagicMock(exists=MagicMock(return_value=True), unlink=MagicMock()),
        )
        command = "apply" if action == "deploy" else action

        # pylint: disable=no-member
        # module is skipped
        obj = Terraform(runway_context, tmp_path)
        assert not obj[action]()
        obj.handle_backend.assert_called_once_with()
        obj.cleanup_dot_terraform.assert_not_called()
        obj.handle_parameters.assert_not_called()
        obj.auto_tfvars.exists.assert_called_once_with()
        obj.auto_tfvars.unlink.assert_called_once_with()
        caplog.clear()

        # module is run; workspace matches
        obj.auto_tfvars.exists.return_value = False
        monkeypatch.setattr(obj, "skip", False)
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
        assert "{} (in progress)".format(command) in logs
        assert "{} (complete)".format(command) in logs
        caplog.clear()

        # module is run; switch to workspace
        monkeypatch.setattr(Terraform, "current_workspace", "default")
        assert not obj[action]()
        obj.terraform_workspace_list.assert_called_once_with()
        obj.terraform_workspace_select.assert_called_once_with("test")
        obj.terraform_workspace_new.assert_not_called()
        logs = "\n".join(caplog.messages)
        assert "re-running init after workspace change..." in logs

        # module is run; create workspace
        monkeypatch.setattr(
            Terraform, "terraform_workspace_list", MagicMock(return_value="")
        )
        assert not obj[action]()
        obj.terraform_workspace_new.assert_called_once_with("test")


class TestTerraformOptions(object):
    """Test runway.module.terraform.TerraformOptions."""

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
            ({"terraform_version": {"test": "0.12", "prod": "0.11.6"}}),  # deprecated
            (
                {
                    "args": {
                        "apply": ["-key=apply"],
                        "init": ["-key=init"],
                        "plan": ["-key=plan"],
                    },
                    "terraform_backend_config": {"region": "us-west-2"},
                    "terraform_backend_ssm_params": {
                        "bucket": "foo",
                        "dynamodb_table": "bar",
                    },
                    "terraform_version": {"test": "0.12", "prod": "0.11.6"},
                }
            ),  # deprecated
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
            (
                {
                    "args": ["-key=val"],  # deprecated
                    "terraform_backend_config": {
                        "test": {"bucket": "foo", "dynamodb_table": "bar"},
                        "prod": {"bucket": "invalid", "dynamodb_table": "invalid"},
                    },
                    "terraform_version": {"test": "0.12", "prod": "0.11.6"},
                }
            ),
        ],
    )
    @patch("runway.module.terraform.TerraformBackendConfig.parse")
    def test_parse(self, mock_backend, config, monkeypatch, runway_context):
        """Test parse."""
        mock_backend.return_value = "successfully parsed backend"

        if sys.version_info.major < 3:  # python 2 support

            @staticmethod
            def assert_resolve_version_kwargs(context, terraform_version=None, **_):
                """Assert args passed to the method during parse."""
                assert config.get("terraform_version") == terraform_version
                return "successfully resolved version"

        else:

            def assert_resolve_version_kwargs(context, terraform_version=None, **_):
                """Assert args passed to the method during parse."""
                assert config.get("terraform_version") == terraform_version
                return "successfully resolved version"

        monkeypatch.setattr(
            TerraformOptions, "resolve_version", assert_resolve_version_kwargs
        )

        result = TerraformOptions.parse(context=runway_context, path="./", **config)

        if isinstance(config.get("args"), list):
            assert result.args["apply"] == config["args"]
            assert result.args["init"] == []
            assert result.args["plan"] == []
        elif isinstance(config.get("args"), dict):
            assert result.args["apply"] == config["args"].get("apply", [])
            assert result.args["init"] == config["args"].get("init", [])
            assert result.args["plan"] == config["args"].get("plan", [])
        assert result.backend_config == "successfully parsed backend"
        assert result.version == "successfully resolved version"
        mock_backend.assert_called_once_with(runway_context, "./", **config)

    @pytest.mark.parametrize(
        "terraform_version, expected, exception",
        [
            ("0.11.6", "0.11.6", does_not_raise()),
            (
                {"test": "0.12", "prod": "0.11.6"},  # deprecated
                "0.12",
                does_not_raise(),
            ),
            ({"*": "0.11.6", "test": "0.12"}, "0.12", does_not_raise()),  # deprecated
            ({"*": "0.11.6", "prod": "0.12"}, "0.11.6", does_not_raise()),  # deprecated
            ({"prod": "0.11.6"}, None, does_not_raise()),  # deprecated
            (None, None, does_not_raise()),
            (13, None, pytest.raises(TypeError)),
        ],
    )
    def test_resolve_version(
        self, runway_context, terraform_version, expected, exception
    ):
        """Test resolve_version."""
        config = {"something": None}
        if terraform_version:
            config["terraform_version"] = terraform_version
        with exception:
            assert (
                TerraformOptions.resolve_version(runway_context, **config) == expected
            )


class TestTerraformBackendConfig(object):
    """Test runway.module.terraform.TerraformBackendConfig."""

    def test_get_full_configuration(self, runway_context, tmp_path):
        """Test get_full_configuration."""
        config_file = tmp_path / "backend.hcl"
        config_file.write_text(six.u('key2 = "val2"'))
        backend = TerraformBackendConfig(runway_context, **{"key1": "val1"})
        assert backend.get_full_configuration() == {"key1": "val1"}
        backend.config_file = config_file
        assert backend.get_full_configuration() == {"key1": "val1", "key2": "val2"}

    @pytest.mark.skipif(sys.version_info.major < 3, reason="python 2 dict is unordered")
    @pytest.mark.parametrize(
        "input_data, expected_items",
        [
            ({}, []),
            ({"some-key": "anything"}, ["some-key=anything"]),
            ({"dynamodb_table": "test-table"}, ["dynamodb_table=test-table"]),
            ({"region": "us-east-1"}, ["region=us-east-1"]),
            (
                {"bucket": "test-bucket", "dynamodb_table": "test-table"},
                ["bucket=test-bucket", "dynamodb_table=test-table"],
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
                    "config_file": MagicMock(),
                },
                ["bucket=test-bucket", "dynamodb_table=test-table", "region=us-east-1"],
            ),
        ],
    )
    def test_init_args(self, input_data, expected_items, runway_context):
        """Test init_args."""
        expected = []
        for i in expected_items:
            expected.extend(["-backend-config", i])
        assert (
            TerraformBackendConfig(runway_context, **input_data).init_args == expected
        )

    def test_init_args_file(self, caplog, runway_context, tmp_path):
        """Test init_args with backend file."""
        caplog.set_level(LogLevels.VERBOSE, logger=MODULE)
        config_file = tmp_path / "backend.hcl"
        assert TerraformBackendConfig(
            runway_context, config_file=config_file
        ).init_args == ["-backend-config=backend.hcl"]
        assert "using backend config file: backend.hcl" in caplog.messages

    @pytest.mark.parametrize(
        "kwargs, stack_info,expected",
        [
            (
                {
                    "bucket": "tf-state::BucketName",
                    "dynamodb_table": "tf-state::TableName",
                },
                {"tf-state": {"BucketName": "test-bucket", "TableName": "test-table"}},
                {"bucket": "test-bucket", "dynamodb_table": "test-table"},
            ),
            ({}, {}, {}),
        ],
    )
    def test_resolve_cfn_outputs(self, kwargs, stack_info, expected):
        """Test resolve_cfn_outputs."""
        client = boto3.client("cloudformation")
        stubber = Stubber(client)
        for stack, outputs in stack_info.items():
            for key, val in outputs.items():
                stubber.add_response(
                    "describe_stacks",
                    {
                        "Stacks": [
                            {
                                "StackName": stack,
                                "CreationTime": datetime.now(),
                                "StackStatus": "CREATE_COMPLETE",
                                "Outputs": [{"OutputKey": key, "OutputValue": val}],
                            }
                        ]
                    },
                )
        with stubber:
            assert (
                TerraformBackendConfig.resolve_cfn_outputs(client, **kwargs) == expected
            )
        stubber.assert_no_pending_responses()

    @pytest.mark.parametrize(
        "kwargs, parameters, expected",
        [
            (
                {"bucket": "/some/param/key", "dynamodb_table": "foo"},
                [
                    {"name": "/some/param/key", "value": "test-bucket"},
                    {"name": "foo", "value": "test-table"},
                ],
                {"bucket": "test-bucket", "dynamodb_table": "test-table"},
            ),
            ({}, {}, {}),
        ],
    )
    @pytest.mark.skipif(
        sys.version_info.major < 3,
        reason="python 2 dict handling prevents this from " "reliably passing",
    )
    def test_resolve_ssm_params(self, caplog, kwargs, parameters, expected):
        """Test resolve_ssm_params."""
        # this test is not compatable with python 2 due to how it handles dicts
        caplog.set_level("WARNING")

        client = boto3.client("ssm")
        stubber = Stubber(client)

        for param in parameters:
            stubber.add_response(
                "get_parameter",
                {
                    "Parameter": {
                        "Name": param["name"],
                        "Value": param["value"],
                        "LastModifiedDate": datetime.now(),
                    }
                },
                {"Name": param["name"], "WithDecryption": True},
            )

        with stubber:
            assert (
                TerraformBackendConfig.resolve_ssm_params(client, **kwargs) == expected
            )
        stubber.assert_no_pending_responses()
        assert "deprecated" in "\n".join(caplog.messages)

    def test_gen_backend_filenames(self):
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
    def test_get_backend_file(self, tmp_path, filename, expected):
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
                {
                    "terraform_backend_config": {
                        "bucket": "foo",
                        "dynamodb_table": "bar",
                        "region": "us-west-2",
                    }
                },
                "us-west-2",
            ),
            (
                {
                    "terraform_backend_config": {"region": "us-west-2"},
                    "terraform_backend_cfn_outputs": {
                        "bucket": "foo",
                        "dynamodb_table": "bar",
                    },
                },
                "us-west-2",
            ),
            (
                {
                    "terraform_backend_config": {"region": "us-west-2"},
                    "terraform_backend_ssm_params": {  # deprecated
                        "bucket": "foo",
                        "dynamodb_table": "bar",
                    },
                },
                "us-west-2",
            ),
            (
                {
                    "terraform_backend_config": {
                        "bucket": "foo",
                        "dynamodb_table": "bar",
                    }
                },
                "us-east-1",
            ),
            (
                {
                    "terraform_backend_cfn_outputs": {
                        "bucket": "foo",
                        "dynamodb_table": "bar",
                    }
                },
                "us-east-1",
            ),
            (
                {
                    "terraform_backend_ssm_params": {  # deprecated
                        "bucket": "foo",
                        "dynamodb_table": "bar",
                    }
                },
                "us-east-1",
            ),
            (
                {
                    "terraform_backend_cfn_outputs": {
                        "bucket": "foo",
                        "dynamodb_table": "bar",
                    }
                },
                "us-east-1",
            ),
            (
                {
                    "terraform_backend_ssm_params": {  # deprecated
                        "bucket": "foo",
                        "dynamodb_table": "bar",
                    }
                },
                "us-east-1",
            ),
            (
                {
                    "terraform_backend_cfn_outputs": {"bucket": "foo"},
                    "terraform_backend_ssm_params": {  # deprecated
                        "dynamodb_table": "bar"
                    },
                },
                "us-east-1",
            ),
            (
                {
                    "terraform_backend_config": {
                        "bucket": "nope",
                        "dynamodb_table": "nope",
                        "region": "us-west-2",
                    },
                    "terraform_backend_cfn_outputs": {
                        "bucket": "foo",
                        "dynamodb_table": "bar",
                    },
                },
                "us-west-2",
            ),
            (
                {
                    "terraform_backend_config": {
                        "bucket": "nope",
                        "dynamodb_table": "nope",
                        "region": "us-west-2",
                    },
                    "terraform_backend_ssm_params": {  # deprecated
                        "bucket": "foo",
                        "dynamodb_table": "bar",
                    },
                },
                "us-west-2",
            ),
            (
                {
                    "terraform_backend_cfn_outputs": {
                        "bucket": "nope",
                        "dynamodb_table": "nope",
                    },
                    "terraform_backend_ssm_params": {  # deprecated
                        "bucket": "foo",
                        "dynamodb_table": "bar",
                    },
                },
                "us-east-1",
            ),
            (
                {
                    "terraform_backend_config": {
                        "test": {  # deprecated
                            "bucket": "foo",
                            "dynamodb_table": "bar",
                        },
                        "prod": {"bucket": "invalid", "dynamodb_table": "invalid"},
                    }
                },
                "us-east-1",
            ),
        ],
    )
    def test_parse(self, monkeypatch, runway_context, config, expected_region):
        """Test parse."""
        runway_context.add_stubber("cloudformation", expected_region)
        runway_context.add_stubber("ssm", expected_region)

        if sys.version_info.major < 3:  # python 2 support

            @staticmethod
            def assert_cfn_kwargs(client, **kwargs):
                """Assert args passed to the method during parse."""
                assert kwargs == config.get("terraform_backend_cfn_outputs")
                return kwargs

            @staticmethod
            def assert_ssm_kwargs(client, **kwargs):
                """Assert args passed to the method during parse."""
                assert kwargs == config.get("terraform_backend_ssm_params")
                return kwargs

            @classmethod
            def assert_get_backend_file_args(_, path, env_name, env_region):
                """Assert args passed to the method during parse."""
                assert path == "./"
                assert env_name == "test"
                assert env_region == "us-east-1"
                return "success"

        else:

            def assert_cfn_kwargs(client, **kwargs):
                """Assert args passed to the method during parse."""
                assert kwargs == config.get("terraform_backend_cfn_outputs")
                return kwargs

            def assert_ssm_kwargs(client, **kwargs):
                """Assert args passed to the method during parse."""
                assert kwargs == config.get("terraform_backend_ssm_params")
                return kwargs

            def assert_get_backend_file_args(path, env_name, env_region):
                """Assert args passed to the method during parse."""
                assert path == "./"
                assert env_name == "test"
                assert env_region == "us-east-1"
                return "success"

        monkeypatch.setattr(
            TerraformBackendConfig, "resolve_cfn_outputs", assert_cfn_kwargs
        )
        monkeypatch.setattr(
            TerraformBackendConfig, "resolve_ssm_params", assert_ssm_kwargs
        )
        monkeypatch.setattr(
            TerraformBackendConfig, "get_backend_file", assert_get_backend_file_args
        )

        result = TerraformBackendConfig.parse(runway_context, "./", **config)

        assert result._raw_config["bucket"] == "foo"
        assert result._raw_config["dynamodb_table"] == "bar"
        assert result._raw_config["region"] == expected_region
        assert result.config_file == "success"
