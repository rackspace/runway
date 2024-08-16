"""Test runway.module.cdk."""

from __future__ import annotations

import logging
from subprocess import CalledProcessError
from typing import TYPE_CHECKING, Any, Optional
from unittest.mock import Mock, call

import pytest

from runway.config.models.runway.options.cdk import RunwayCdkModuleOptionsDataModel
from runway.module.cdk import CloudDevelopmentKit, CloudDevelopmentKitOptions

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture
    from pytest_subprocess import FakeProcess
    from pytest_subprocess.fake_popen import FakePopen

    from runway.context import RunwayContext
    from runway.module.cdk import CdkCommandTypeDef

MODULE = "runway.module.cdk"


@pytest.mark.usefixtures("patch_module_npm")
class TestCloudDevelopmentKit:
    """Test CloudDevelopmentKit."""

    def test_cdk_bootstrap(
        self,
        caplog: pytest.LogCaptureFixture,
        mocker: MockerFixture,
        runway_context: RunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test cdk_bootstrap."""
        caplog.set_level(logging.INFO, logger=MODULE)
        mock_gen_cmd = mocker.patch.object(
            CloudDevelopmentKit, "gen_cmd", return_value=["bootstrap"]
        )
        mock_run_module_command = mocker.patch(f"{MODULE}.run_module_command")
        obj = CloudDevelopmentKit(runway_context, module_root=tmp_path)
        assert not obj.cdk_bootstrap()
        mock_gen_cmd.assert_called_once_with("bootstrap", include_context=True)
        mock_run_module_command.assert_called_once_with(
            cmd_list=mock_gen_cmd.return_value,
            env_vars=runway_context.env.vars,
            logger=obj.logger,
        )
        logs = "\n".join(caplog.messages)
        assert "init (in progress)" in logs
        assert "init (complete)" in logs

    def test_cdk_bootstrap_raise_called_process_error(
        self,
        mocker: MockerFixture,
        runway_context: RunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test cdk_bootstrap raise CalledProcessError."""
        mocker.patch.object(CloudDevelopmentKit, "gen_cmd")
        mocker.patch(f"{MODULE}.run_module_command", side_effect=CalledProcessError(1, ""))
        with pytest.raises(CalledProcessError):
            CloudDevelopmentKit(runway_context, module_root=tmp_path).cdk_bootstrap()

    def test_cdk_deploy(
        self,
        caplog: pytest.LogCaptureFixture,
        mocker: MockerFixture,
        runway_context: RunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test cdk_deploy."""
        caplog.set_level(logging.INFO, logger=MODULE)
        mock_gen_cmd = mocker.patch.object(CloudDevelopmentKit, "gen_cmd", return_value=["deploy"])
        mock_run_module_command = mocker.patch(f"{MODULE}.run_module_command")
        obj = CloudDevelopmentKit(runway_context, module_root=tmp_path)
        assert not obj.cdk_deploy()
        mock_gen_cmd.assert_called_once_with("deploy", ['"*"'], include_context=True)
        mock_run_module_command.assert_called_once_with(
            cmd_list=mock_gen_cmd.return_value,
            env_vars=runway_context.env.vars,
            logger=obj.logger,
        )
        logs = "\n".join(caplog.messages)
        assert "deploy (in progress)" in logs
        assert "deploy (complete)" in logs

    def test_cdk_deploy_raise_called_process_error(
        self,
        mocker: MockerFixture,
        runway_context: RunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test cdk_deploy raise CalledProcessError."""
        mocker.patch.object(CloudDevelopmentKit, "gen_cmd")
        mocker.patch(f"{MODULE}.run_module_command", side_effect=CalledProcessError(1, ""))
        with pytest.raises(CalledProcessError):
            CloudDevelopmentKit(runway_context, module_root=tmp_path).cdk_deploy()

    def test_cdk_destroy(
        self,
        caplog: pytest.LogCaptureFixture,
        mocker: MockerFixture,
        runway_context: RunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test cdk_destroy."""
        caplog.set_level(logging.INFO, logger=MODULE)
        mock_gen_cmd = mocker.patch.object(CloudDevelopmentKit, "gen_cmd", return_value=["destroy"])
        mock_run_module_command = mocker.patch(f"{MODULE}.run_module_command")
        obj = CloudDevelopmentKit(runway_context, module_root=tmp_path)
        assert not obj.cdk_destroy()
        mock_gen_cmd.assert_called_once_with("destroy", ['"*"'], include_context=True)
        mock_run_module_command.assert_called_once_with(
            cmd_list=mock_gen_cmd.return_value,
            env_vars=runway_context.env.vars,
            logger=obj.logger,
        )
        logs = "\n".join(caplog.messages)
        assert "destroy (in progress)" in logs
        assert "destroy (complete)" in logs

    def test_cdk_destroy_raise_called_process_error(
        self,
        mocker: MockerFixture,
        runway_context: RunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test cdk_destroy raise CalledProcessError."""
        mocker.patch.object(CloudDevelopmentKit, "gen_cmd")
        mocker.patch(f"{MODULE}.run_module_command", side_effect=CalledProcessError(1, ""))
        with pytest.raises(CalledProcessError):
            CloudDevelopmentKit(runway_context, module_root=tmp_path).cdk_destroy()

    def test_cdk_diff(
        self,
        caplog: pytest.LogCaptureFixture,
        mocker: MockerFixture,
        runway_context: RunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test cdk_diff."""
        caplog.set_level(logging.INFO, logger=MODULE)
        mock_gen_cmd = mocker.patch.object(CloudDevelopmentKit, "gen_cmd", return_value=["diff"])
        mock_run_module_command = mocker.patch(f"{MODULE}.run_module_command")
        obj = CloudDevelopmentKit(runway_context, module_root=tmp_path)
        assert not obj.cdk_diff()
        mock_gen_cmd.assert_called_once_with("diff", args_list=None, include_context=True)
        mock_run_module_command.assert_called_once_with(
            cmd_list=mock_gen_cmd.return_value,
            env_vars=runway_context.env.vars,
            exit_on_error=False,
            logger=obj.logger,
        )
        logs = "\n".join(caplog.messages)
        assert "plan (in progress)" in logs
        assert "plan (complete)" in logs
        assert not obj.cdk_diff("stack_name")
        mock_gen_cmd.assert_called_with("diff", args_list=["stack_name"], include_context=True)

    @pytest.mark.parametrize("return_code", [1, 2])
    def test_cdk_diff_catch_called_process_error_sys_exit(
        self,
        mocker: MockerFixture,
        return_code: int,
        runway_context: RunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test cdk_diff catch CalledProcessError and call sys.exit() with return code."""
        mocker.patch.object(CloudDevelopmentKit, "gen_cmd")
        mocker.patch(
            f"{MODULE}.run_module_command",
            side_effect=CalledProcessError(return_code, ""),
        )
        with pytest.raises(SystemExit) as excinfo:
            CloudDevelopmentKit(runway_context, module_root=tmp_path).cdk_diff()
        assert excinfo.value.args == (return_code,)

    def test_cdk_list(
        self,
        fake_process: FakeProcess,
        mocker: MockerFixture,
        runway_context: RunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test cdk_list."""
        mock_gen_cmd = mocker.patch.object(CloudDevelopmentKit, "gen_cmd", return_value=["list"])
        fake_process.register_subprocess(
            mock_gen_cmd.return_value, returncode=0, stdout="Stack0\nStack1"
        )
        obj = CloudDevelopmentKit(runway_context, module_root=tmp_path)
        assert obj.cdk_list() == ["Stack0", "Stack1"]
        mock_gen_cmd.assert_called_once_with("list", include_context=True)
        assert fake_process.call_count(mock_gen_cmd.return_value) == 1

    def test_cdk_list_empty(
        self,
        fake_process: FakeProcess,
        mocker: MockerFixture,
        runway_context: RunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test cdk_list empty."""
        mock_gen_cmd = mocker.patch.object(CloudDevelopmentKit, "gen_cmd", return_value=["list"])
        fake_process.register_subprocess(mock_gen_cmd.return_value, returncode=0, stdout="")
        obj = CloudDevelopmentKit(runway_context, module_root=tmp_path)
        assert obj.cdk_list() == [""]
        assert fake_process.call_count(mock_gen_cmd.return_value) == 1

    def test_cdk_list_raise_called_process_error(
        self,
        fake_process: FakeProcess,
        mocker: MockerFixture,
        runway_context: RunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test cdk_list raise CalledProcessError."""
        mock_gen_cmd = mocker.patch.object(CloudDevelopmentKit, "gen_cmd", return_value=["list"])
        fake_process.register_subprocess(
            mock_gen_cmd.return_value,
            returncode=1,
        )
        with pytest.raises(CalledProcessError):
            CloudDevelopmentKit(runway_context, module_root=tmp_path).cdk_list()
        assert fake_process.call_count(mock_gen_cmd.return_value) == 1

    @pytest.mark.parametrize(
        "debug, no_color, verbose, expected",
        [
            (False, False, False, []),
            (True, False, False, ["--debug"]),
            (True, True, False, ["--no-color", "--debug"]),
            (True, True, True, ["--no-color", "--debug"]),
            (False, True, False, ["--no-color"]),
            (False, True, True, ["--no-color", "--verbose"]),
            (False, False, True, ["--verbose"]),
        ],
    )
    def test_cli_args(
        self,
        debug: bool,
        expected: list[str],
        no_color: bool,
        tmp_path: Path,
        verbose: bool,
    ) -> None:
        """Test cli_args."""
        assert (
            CloudDevelopmentKit(
                Mock(env=Mock(debug=debug, verbose=verbose), no_color=no_color),
                module_root=tmp_path,
            ).cli_args
            == expected
        )

    @pytest.mark.parametrize(
        "parameters, expected",
        [
            ({}, ["--context", "environment=test"]),
            ({"key": "val"}, ["--context", "environment=test", "--context", "key=val"]),
            (
                {"environment": "override", "key": "val"},
                ["--context", "environment=override", "--context", "key=val"],
            ),
            ({"environment": "override"}, ["--context", "environment=override"]),
        ],
    )
    def test_cli_args_context(
        self,
        expected: list[str],
        runway_context: RunwayContext,
        parameters: dict[str, Any],
        tmp_path: Path,
    ) -> None:
        """Test cli_args_context."""
        assert (
            CloudDevelopmentKit(
                runway_context, module_root=tmp_path, parameters=parameters
            ).cli_args_context
            == expected
        )

    @pytest.mark.parametrize("skip", [False, True])
    def test_deploy(
        self,
        mocker: MockerFixture,
        runway_context: RunwayContext,
        skip: bool,
        tmp_path: Path,
    ) -> None:
        """Test deploy."""
        mocker.patch.object(CloudDevelopmentKit, "skip", skip)
        cdk_bootstrap = mocker.patch.object(CloudDevelopmentKit, "cdk_bootstrap")
        cdk_deploy = mocker.patch.object(CloudDevelopmentKit, "cdk_deploy")
        npm_install = mocker.patch.object(CloudDevelopmentKit, "npm_install")
        run_build_steps = mocker.patch.object(CloudDevelopmentKit, "run_build_steps")
        assert not CloudDevelopmentKit(runway_context, module_root=tmp_path).deploy()
        if skip:
            cdk_bootstrap.assert_not_called()
            cdk_deploy.assert_not_called()
            npm_install.assert_not_called()
            run_build_steps.assert_not_called()
        else:
            cdk_bootstrap.assert_called_once_with()
            cdk_deploy.assert_called_once_with()
            npm_install.assert_called_once_with()
            run_build_steps.assert_called_once_with()

    @pytest.mark.parametrize("skip", [False, True])
    def test_destroy(
        self,
        mocker: MockerFixture,
        runway_context: RunwayContext,
        skip: bool,
        tmp_path: Path,
    ) -> None:
        """Test destroy."""
        mocker.patch.object(CloudDevelopmentKit, "skip", skip)
        cdk_bootstrap = mocker.patch.object(CloudDevelopmentKit, "cdk_bootstrap")
        cdk_destroy = mocker.patch.object(CloudDevelopmentKit, "cdk_destroy")
        npm_install = mocker.patch.object(CloudDevelopmentKit, "npm_install")
        run_build_steps = mocker.patch.object(CloudDevelopmentKit, "run_build_steps")
        assert not CloudDevelopmentKit(runway_context, module_root=tmp_path).destroy()
        cdk_bootstrap.assert_not_called()
        if skip:
            cdk_destroy.assert_not_called()
            npm_install.assert_not_called()
            run_build_steps.assert_not_called()
        else:
            cdk_destroy.assert_called_once_with()
            npm_install.assert_called_once_with()
            run_build_steps.assert_called_once_with()

    @pytest.mark.parametrize(
        "command, args_list, include_context, env_ci, expected",
        [
            (
                "deploy",
                ['"*"'],
                True,
                False,
                ["deploy", "cli_args", '"*"', "cli_args_context"],
            ),
            (
                "deploy",
                ['"*"'],
                True,
                True,
                [
                    "deploy",
                    "cli_args",
                    '"*"',
                    "cli_args_context",
                    "--ci",
                    "--require-approval=never",
                ],
            ),
            (
                "destroy",
                ['"*"'],
                True,
                False,
                ["destroy", "cli_args", '"*"', "cli_args_context"],
            ),
            (
                "destroy",
                ['"*"'],
                True,
                True,
                ["destroy", "cli_args", '"*"', "cli_args_context", "--force"],
            ),
            ("init", None, True, False, ["init", "cli_args", "cli_args_context"]),
            ("init", None, True, True, ["init", "cli_args", "cli_args_context"]),
            ("list", None, False, False, ["list", "cli_args"]),
            ("list", None, False, True, ["list", "cli_args"]),
        ],
    )
    def test_gen_cmd(
        self,
        args_list: Optional[list[str]],
        command: CdkCommandTypeDef,
        env_ci: bool,
        expected: list[str],
        include_context: bool,
        mocker: MockerFixture,
        runway_context: RunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test gen_cmd."""
        mocker.patch.object(CloudDevelopmentKit, "cli_args", ["cli_args"])
        mocker.patch.object(CloudDevelopmentKit, "cli_args_context", ["cli_args_context"])
        generate_node_command = mocker.patch(
            f"{MODULE}.generate_node_command", return_value=["success"]
        )
        runway_context.env.ci = env_ci
        obj = CloudDevelopmentKit(runway_context, module_root=tmp_path)
        assert (
            obj.gen_cmd(command, args_list, include_context=include_context)
            == generate_node_command.return_value
        )
        generate_node_command.assert_called_once_with(
            command="cdk",
            command_opts=expected,
            logger=obj.logger,
            package="aws-cdk",
            path=obj.path,
        )

    @pytest.mark.parametrize("skip", [False, True])
    def test_init(
        self,
        mocker: MockerFixture,
        runway_context: RunwayContext,
        skip: bool,
        tmp_path: Path,
    ) -> None:
        """Test init."""
        mocker.patch.object(CloudDevelopmentKit, "skip", skip)
        cdk_bootstrap = mocker.patch.object(CloudDevelopmentKit, "cdk_bootstrap")
        npm_install = mocker.patch.object(CloudDevelopmentKit, "npm_install")
        run_build_steps = mocker.patch.object(CloudDevelopmentKit, "run_build_steps")
        assert not CloudDevelopmentKit(runway_context, module_root=tmp_path).init()
        if skip:
            cdk_bootstrap.assert_not_called()
            npm_install.assert_not_called()
            run_build_steps.assert_not_called()
        else:
            cdk_bootstrap.assert_called_once_with()
            npm_install.assert_called_once_with()
            run_build_steps.assert_called_once_with()

    @pytest.mark.parametrize("skip", [False, True])
    def test_plan(
        self,
        mocker: MockerFixture,
        runway_context: RunwayContext,
        skip: bool,
        tmp_path: Path,
    ) -> None:
        """Test plan."""
        mocker.patch.object(CloudDevelopmentKit, "skip", skip)
        cdk_bootstrap = mocker.patch.object(CloudDevelopmentKit, "cdk_bootstrap")
        cdk_list = mocker.patch.object(
            CloudDevelopmentKit, "cdk_list", return_value=["Stack0", "Stack1"]
        )
        cdk_diff = mocker.patch.object(CloudDevelopmentKit, "cdk_diff")
        npm_install = mocker.patch.object(CloudDevelopmentKit, "npm_install")
        run_build_steps = mocker.patch.object(CloudDevelopmentKit, "run_build_steps")
        assert not CloudDevelopmentKit(runway_context, module_root=tmp_path).plan()
        cdk_bootstrap.assert_not_called()
        if skip:
            cdk_list.assert_not_called()
            cdk_diff.assert_not_called()
            npm_install.assert_not_called()
            run_build_steps.assert_not_called()
        else:
            cdk_list.assert_called_once_with()
            cdk_diff.assert_has_calls([call("Stack0"), call("Stack1")])
            npm_install.assert_called_once_with()
            run_build_steps.assert_called_once_with()

    def test_run_build_steps_empty(
        self,
        caplog: pytest.LogCaptureFixture,
        fake_process: FakeProcess,  # noqa: ARG002
        runway_context: RunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test run_build_steps."""
        caplog.set_level(logging.INFO, logger=MODULE)
        obj = CloudDevelopmentKit(runway_context, module_root=tmp_path, options={"build_steps": []})
        assert not obj.run_build_steps()
        logs = "\n".join(caplog.messages)
        assert "build steps (in progress)" not in logs
        assert "build steps (complete)" not in logs

    def test_run_build_steps_linux(
        self,
        caplog: pytest.LogCaptureFixture,
        fake_process: FakeProcess,
        mocker: MockerFixture,
        platform_linux: None,  # noqa: ARG002
        runway_context: RunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test run_build_steps."""
        caplog.set_level(logging.INFO, logger=MODULE)
        fix_windows_command_list = mocker.patch(f"{MODULE}.fix_windows_command_list")
        fake_process.register_subprocess(["test", "step"], returncode=0)
        obj = CloudDevelopmentKit(
            runway_context, module_root=tmp_path, options={"build_steps": ["test step"]}
        )
        assert not obj.run_build_steps()
        fix_windows_command_list.assert_not_called()
        assert fake_process.call_count(["test", "step"]) == 1
        logs = "\n".join(caplog.messages)
        assert "build steps (in progress)" in logs
        assert "build steps (complete)" in logs

    def test_run_build_steps_raise_file_not_found(
        self,
        caplog: pytest.LogCaptureFixture,
        fake_process: FakeProcess,
        platform_linux: None,  # noqa: ARG002
        runway_context: RunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test run_build_steps."""
        caplog.set_level(logging.ERROR, MODULE)

        def _callback(process: FakePopen) -> None:
            process.returncode = 1
            raise FileNotFoundError

        fake_process.register_subprocess(["test", "step"], callback=_callback)
        with pytest.raises(FileNotFoundError):
            CloudDevelopmentKit(
                runway_context,
                module_root=tmp_path,
                options={"build_steps": ["test step"]},
            ).run_build_steps()
        assert fake_process.call_count(["test", "step"]) == 1
        assert "failed to find it" in "\n".join(caplog.messages)

    def test_run_build_steps_raise_called_process_error(
        self,
        fake_process: FakeProcess,
        platform_linux: None,  # noqa: ARG002
        runway_context: RunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test run_build_steps."""
        fake_process.register_subprocess(["test", "step"], returncode=1)
        with pytest.raises(CalledProcessError):
            CloudDevelopmentKit(
                runway_context,
                module_root=tmp_path,
                options={"build_steps": ["test step"]},
            ).run_build_steps()
        assert fake_process.call_count(["test", "step"]) == 1

    def test_run_build_steps_windows(
        self,
        caplog: pytest.LogCaptureFixture,
        fake_process: FakeProcess,
        mocker: MockerFixture,
        platform_windows: None,  # noqa: ARG002
        runway_context: RunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test run_build_steps."""
        caplog.set_level(logging.INFO, logger=MODULE)
        fix_windows_command_list = mocker.patch(
            f"{MODULE}.fix_windows_command_list", return_value=["test", "step"]
        )
        fake_process.register_subprocess(["test", "step"], returncode=0)
        obj = CloudDevelopmentKit(
            runway_context, module_root=tmp_path, options={"build_steps": ["test step"]}
        )
        assert not obj.run_build_steps()
        fix_windows_command_list.assert_called_once_with(["test", "step"])
        assert fake_process.call_count(["test", "step"]) == 1
        logs = "\n".join(caplog.messages)
        assert "build steps (in progress)" in logs
        assert "build steps (complete)" in logs

    @pytest.mark.parametrize(
        "explicitly_enabled, package_json_missing, expected",
        [
            (False, False, True),
            (True, False, False),
            (True, True, True),
            (False, True, True),
        ],
    )
    def test_skip(
        self,
        caplog: pytest.LogCaptureFixture,
        expected: bool,
        explicitly_enabled: bool,
        mocker: MockerFixture,
        package_json_missing: bool,
        runway_context: RunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test skip."""
        caplog.set_level(logging.INFO, logger=MODULE)
        mocker.patch.object(
            CloudDevelopmentKit,
            "package_json_missing",
            return_value=package_json_missing,
        )
        assert (
            CloudDevelopmentKit(
                runway_context,
                explicitly_enabled=explicitly_enabled,
                module_root=tmp_path,
            ).skip
            is expected
        )
        if package_json_missing:
            assert "skipped; package.json" in "\n".join(caplog.messages)
        elif not explicitly_enabled:
            assert "skipped; environment required but not defined" in "\n".join(caplog.messages)


class TestCloudDevelopmentKitOptions:
    """Test CloudDevelopmentKitOptions."""

    def test___init__(self) -> None:
        """Test __init__."""
        data = RunwayCdkModuleOptionsDataModel(build_steps=["test"])
        obj = CloudDevelopmentKitOptions(data)
        assert obj.build_steps == data.build_steps
        assert obj.skip_npm_ci == data.skip_npm_ci

    def test_parse_obj(self) -> None:
        """Test parse_obj."""
        config = {"build_steps": ["test-cmd"], "skip_npm_ci": True, "key": "val"}
        obj = CloudDevelopmentKitOptions.parse_obj(config)
        assert isinstance(obj.data, RunwayCdkModuleOptionsDataModel)
        assert obj.data.build_steps == config["build_steps"]
        assert obj.data.skip_npm_ci == config["skip_npm_ci"]
        assert "key" not in obj.data.model_dump()
