"""Test runway.module.serverless."""

# pyright: basic, reportFunctionMemberAccess=none
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, cast

import pytest
import yaml
from mock import ANY, MagicMock, Mock, call
from pydantic import ValidationError

from runway.config.models.runway.options.serverless import (
    RunwayServerlessModuleOptionsDataModel,
)
from runway.module.serverless import (
    Serverless,
    ServerlessArtifact,
    ServerlessOptions,
    gen_sls_config_files,
)

if TYPE_CHECKING:
    from pytest import LogCaptureFixture
    from pytest_mock import MockerFixture
    from pytest_subprocess.fake_process import FakeProcess

    from runway.type_defs import AnyPathConstrained

    from ..factories import MockRunwayContext

MODULE = "runway.module.serverless"


@pytest.mark.usefixtures("patch_module_npm")
class TestServerless:
    """Test runway.module.serverless.Serverless."""

    def test___init__(self, runway_context: MockRunwayContext, tmp_path: Path) -> None:
        """Test __init__ and the attributes set in __init__."""
        obj = Serverless(
            runway_context, module_root=tmp_path, options={"skip_npm_ci": True}
        )
        assert isinstance(obj.options, ServerlessOptions)
        assert obj.region == runway_context.env.aws_region
        assert obj.stage == runway_context.env.name

        with pytest.raises(ValidationError):
            assert not Serverless(
                runway_context,
                module_root=tmp_path,
                options={"promotezip": {"invalid": "value"}},
            )

    def test__deploy_package(
        self,
        caplog: LogCaptureFixture,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        tempfile_temporary_directory: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test _deploy_package."""
        caplog.set_level(logging.INFO, logger=MODULE)
        sls_deploy = mocker.patch.object(Serverless, "sls_deploy")
        assert not Serverless(  # pylint: disable=protected-access
            runway_context, module_root=tmp_path
        )._deploy_package()
        tempfile_temporary_directory.assert_not_called()
        sls_deploy.assert_called_once_with()
        assert f"{tmp_path.name}:deploy (in progress)" in caplog.messages
        assert f"{tmp_path.name}:deploy (complete)" in caplog.messages

    def test__deploy_package_promotezip(
        self,
        caplog: LogCaptureFixture,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        tempfile_temporary_directory: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test _deploy_package."""
        caplog.set_level(logging.INFO, logger=MODULE)
        artifact = Mock(package_path=tmp_path)
        artifact_class = mocker.patch(
            f"{MODULE}.ServerlessArtifact", return_value=artifact
        )
        sls_deploy = mocker.patch.object(Serverless, "sls_deploy")
        sls_package = mocker.patch.object(
            Serverless, "sls_package", return_value=str(tmp_path)
        )
        sls_print = mocker.patch.object(
            Serverless, "sls_print", return_value="print output"
        )
        obj = Serverless(
            runway_context,
            module_root=tmp_path,
            options={"promotezip": {"bucketname": "test-bucket"}},
        )
        assert not obj._deploy_package()  # pylint: disable=protected-access
        tempfile_temporary_directory.assert_called_once_with(
            dir=runway_context.work_dir
        )
        sls_print.assert_called_once()
        artifact_class.assert_called_once_with(
            runway_context,
            sls_print.return_value,
            logger=obj.logger,
            package_path=str(tmp_path),
            path=tmp_path,
        )
        sls_package.assert_called_once_with(output_path=tmp_path, skip_install=True)
        artifact.sync_with_s3.assert_called_once_with("test-bucket")
        sls_deploy.assert_called_once_with(package=tmp_path, skip_install=True)
        assert f"{tmp_path.name}:package (in progress)" in caplog.messages
        assert f"{tmp_path.name}:package (complete)" in caplog.messages
        assert f"{tmp_path.name}:deploy (in progress)" in caplog.messages
        assert f"{tmp_path.name}:deploy (complete)" in caplog.messages

    def test_cli_args(self, runway_context: MockRunwayContext, tmp_path: Path) -> None:
        """Test cli_args."""
        obj = Serverless(runway_context, module_root=tmp_path)

        assert obj.cli_args == [
            "--region",
            runway_context.env.aws_region,
            "--stage",
            runway_context.env.name,
        ]

        runway_context.env.vars["DEBUG"] = "1"
        assert obj.cli_args == [
            "--region",
            runway_context.env.aws_region,
            "--stage",
            runway_context.env.name,
            "--verbose",
        ]

    @pytest.mark.parametrize("skip", [False, True])
    def test_deploy(
        self,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        skip: bool,
        tmp_path: Path,
    ) -> None:
        """Test deploy."""
        deploy_package = mocker.patch.object(Serverless, "_deploy_package")
        extend_serverless_yml = mocker.patch.object(Serverless, "extend_serverless_yml")
        mocker.patch.object(Serverless, "skip", skip)
        assert not Serverless(runway_context, module_root=tmp_path).deploy()
        if skip:
            deploy_package.assert_not_called()
            extend_serverless_yml.assert_not_called()
        else:
            deploy_package.assert_called_once_with()
            extend_serverless_yml.assert_not_called()

    @pytest.mark.parametrize("skip", [False, True])
    def test_deploy_extend_serverless_yml(
        self,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        skip: bool,
        tmp_path: Path,
    ) -> None:
        """Test deploy."""
        deploy_package = mocker.patch.object(Serverless, "_deploy_package")
        extend_serverless_yml = mocker.patch.object(Serverless, "extend_serverless_yml")
        mocker.patch.object(Serverless, "skip", skip)
        assert not Serverless(
            runway_context,
            module_root=tmp_path,
            options={"extend_serverless_yml": {"config": {"foo": "bar"}}},
        ).deploy()
        if skip:
            deploy_package.assert_not_called()
            extend_serverless_yml.assert_not_called()
        else:
            deploy_package.assert_not_called()
            extend_serverless_yml.assert_called_once_with(deploy_package)

    @pytest.mark.parametrize("skip", [False, True])
    def test_destroy(
        self,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        skip: bool,
        tmp_path: Path,
    ) -> None:
        """Test destroy."""
        sls_remove = mocker.patch.object(Serverless, "sls_remove")
        extend_serverless_yml = mocker.patch.object(Serverless, "extend_serverless_yml")
        mocker.patch.object(Serverless, "skip", skip)
        assert not Serverless(runway_context, module_root=tmp_path).destroy()
        if skip:
            sls_remove.assert_not_called()
            extend_serverless_yml.assert_not_called()
        else:
            sls_remove.assert_called_once_with()
            extend_serverless_yml.assert_not_called()

    @pytest.mark.parametrize("skip", [False, True])
    def test_destroy_extend_serverless_yml(
        self,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        skip: bool,
        tmp_path: Path,
    ) -> None:
        """Test destroy."""
        sls_remove = mocker.patch.object(Serverless, "sls_remove")
        extend_serverless_yml = mocker.patch.object(Serverless, "extend_serverless_yml")
        mocker.patch.object(Serverless, "skip", skip)
        assert not Serverless(
            runway_context,
            module_root=tmp_path,
            options={"extend_serverless_yml": {"config": {"foo": "bar"}}},
        ).destroy()
        if skip:
            sls_remove.assert_not_called()
            extend_serverless_yml.assert_not_called()
        else:
            sls_remove.assert_not_called()
            extend_serverless_yml.assert_called_once_with(sls_remove)

    def test_env_file(self, runway_context: MockRunwayContext, tmp_path: Path) -> None:
        """Test env_file.

        Testing the precedence of each path, create the files in order from
        lowest to highest. After creating the file, the property's value
        is checked then cleared since the value is cached after the first
        time it is resolved.

        """
        env_dir = tmp_path / "env"
        env_dir.mkdir()
        obj = Serverless(runway_context, module_root=tmp_path)
        assert not obj.env_file
        del obj.env_file

        config_test_json = tmp_path / "config-test.json"
        config_test_json.touch()
        assert obj.env_file == config_test_json
        del obj.env_file

        env_test_json = env_dir / "test.json"
        env_test_json.touch()
        assert obj.env_file == env_test_json
        del obj.env_file

        config_test_us_east_1_json = tmp_path / "config-test-us-east-1.json"
        config_test_us_east_1_json.touch()
        assert obj.env_file == config_test_us_east_1_json
        del obj.env_file

        env_test_us_east_1_json = env_dir / "test-us-east-1.json"
        env_test_us_east_1_json.touch()
        assert obj.env_file == env_test_us_east_1_json
        del obj.env_file

        config_test_yml = tmp_path / "config-test.yml"
        config_test_yml.touch()
        assert obj.env_file == config_test_yml
        del obj.env_file

        env_test_yml = env_dir / "test.yml"
        env_test_yml.touch()
        assert obj.env_file == env_test_yml
        del obj.env_file

        config_test_us_east_1_yml = tmp_path / "config-test-us-east-1.yml"
        config_test_us_east_1_yml.touch()
        assert obj.env_file == config_test_us_east_1_yml
        del obj.env_file

        env_test_us_east_1_yml = env_dir / "test-us-east-1.yml"
        env_test_us_east_1_yml.touch()
        assert obj.env_file == env_test_us_east_1_yml
        del obj.env_file

    def test_extend_serverless_yml(
        self,
        caplog: LogCaptureFixture,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test extend_serverless_yml."""
        # pylint: disable=no-member
        mock_merge = mocker.patch("runway.module.serverless.merge_dicts")
        caplog.set_level(logging.DEBUG, logger="runway")
        mock_func = MagicMock()
        mock_merge.return_value = {"key": "val"}
        mocker.patch.object(Serverless, "npm_install", MagicMock())
        mocker.patch.object(Serverless, "sls_print", MagicMock(return_value="original"))
        mocker.patch.object(ServerlessOptions, "update_args", MagicMock())

        options = {"extend_serverless_yml": {"new-key": "val"}}
        obj = Serverless(runway_context, module_root=tmp_path, options=options)

        assert not obj.extend_serverless_yml(mock_func)
        obj.npm_install.assert_called_once()
        obj.sls_print.assert_called_once()
        mock_merge.assert_called_once_with("original", options["extend_serverless_yml"])
        mock_func.assert_called_once_with(skip_install=True)
        obj.options.update_args.assert_called_once_with("config", ANY)

        tmp_file = obj.options.update_args.call_args[0][1]
        # 'no way to check the prefix since it will be a uuid'
        assert tmp_file.endswith(".tmp.serverless.yml")
        assert not (
            tmp_path / tmp_file
        ).exists(), 'should always be deleted after calling "func"'

        caplog.clear()
        mocker.patch(
            "pathlib.Path.unlink", MagicMock(side_effect=OSError("test OSError"))
        )
        assert not obj.extend_serverless_yml(mock_func)
        assert (
            f"{tmp_path.name}:encountered an error when trying to delete the "
            "temporary Serverless config" in caplog.messages
        )

    @pytest.mark.parametrize("command", [("deploy"), ("remove"), ("print")])
    def test_gen_cmd(
        self,
        command: str,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test gen_cmd."""
        mock_cmd = mocker.patch(
            "runway.module.serverless.generate_node_command", return_value=["success"]
        )
        mocker.patch.object(runway_context, "no_color", False)
        obj = Serverless(
            runway_context, module_root=tmp_path, options={"args": ["--config", "test"]}
        )
        expected_opts = [
            command,
            "--region",
            runway_context.env.aws_region,
            "--stage",
            runway_context.env.name,
            "--config",
            "test",
            "--extra-arg",
        ]

        assert obj.gen_cmd(command, args_list=["--extra-arg"]) == ["success"]
        mock_cmd.assert_called_once_with(
            command="sls", command_opts=expected_opts, logger=obj.logger, path=tmp_path
        )
        mock_cmd.reset_mock()

        obj.ctx.env.vars["CI"] = "1"
        mocker.patch.object(runway_context, "no_color", True)
        if command not in ["remove", "print"]:
            expected_opts.append("--conceal")
        assert obj.gen_cmd(command, args_list=["--extra-arg"]) == ["success"]
        mock_cmd.assert_called_once_with(
            command="FORCE_COLOR=0 sls",
            command_opts=expected_opts,
            logger=obj.logger,
            path=tmp_path,
        )

    def test_init(
        self,
        caplog: LogCaptureFixture,
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test init."""
        caplog.set_level(logging.WARNING, logger=MODULE)
        obj = Serverless(runway_context, module_root=tmp_path)
        assert not obj.init()
        assert (
            f"{tmp_path.name}:init not currently supported for {Serverless.__name__}"
            in caplog.messages
        )

    def test_plan(
        self,
        caplog: LogCaptureFixture,
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test plan."""
        caplog.set_level(logging.INFO, logger="runway")
        obj = Serverless(runway_context, module_root=tmp_path)
        assert not obj.plan()
        assert [
            f"{tmp_path.name}:plan not currently supported for Serverless"
        ] == caplog.messages

    def test_skip(
        self,
        caplog: LogCaptureFixture,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test skip."""
        caplog.set_level(logging.INFO, logger="runway")
        obj = Serverless(runway_context, module_root=tmp_path)
        mocker.patch.object(obj, "package_json_missing", lambda: True)
        mocker.patch.object(obj, "env_file", False)

        assert obj.skip
        assert [
            f'{tmp_path.name}:skipped; package.json with "serverless" in devDependencies'
            " is required for this module type"
        ] == caplog.messages
        caplog.clear()

        mocker.patch.object(obj, "package_json_missing", lambda: False)
        assert obj.skip
        assert [
            f"{tmp_path.name}:skipped; config file for this stage/region not found"
            f" -- looking for one of: {', '.join(gen_sls_config_files(obj.stage, obj.region))}"
        ] == caplog.messages
        caplog.clear()

        obj.explicitly_enabled = True
        assert not obj.skip
        obj.explicitly_enabled = False

        obj.parameters = True  # type: ignore
        assert not obj.skip
        obj.parameters = False  # type: ignore

        obj.env_file = True  # type: ignore
        assert not obj.skip

    @pytest.mark.parametrize(
        "package, skip_install", [(None, False), (None, True), ("foobar", False)]
    )
    def test_sls_deploy(
        self,
        mocker: MockerFixture,
        package: Optional[str],
        runway_context: MockRunwayContext,
        skip_install: bool,
        tmp_path: Path,
    ) -> None:
        """Test sls_deploy."""
        gen_cmd = mocker.patch.object(Serverless, "gen_cmd", return_value="cmd")
        npm_install = mocker.patch.object(Serverless, "npm_install")
        run_module_command = mocker.patch(f"{MODULE}.run_module_command")
        obj = Serverless(runway_context, module_root=tmp_path)
        assert not obj.sls_deploy(package=package, skip_install=skip_install)
        if skip_install:
            npm_install.assert_not_called()
        else:
            npm_install.assert_called_once_with()
        if package:
            gen_cmd.assert_called_once_with("deploy", args_list=["--package", package])
        else:
            gen_cmd.assert_called_once_with("deploy", args_list=[])
        run_module_command.assert_called_once_with(
            cmd_list=gen_cmd.return_value, env_vars=obj.ctx.env.vars, logger=obj.logger
        )

    @pytest.mark.parametrize(
        "output_path, skip_install",
        [(None, False), (None, True), ("foobar", False), (Path("./tests"), True)],
    )
    def test_sls_package(
        self,
        mocker: MockerFixture,
        output_path: Optional[AnyPathConstrained],
        runway_context: MockRunwayContext,
        skip_install: bool,
        tmp_path: Path,
    ) -> None:
        """Test sls_package."""
        gen_cmd = mocker.patch.object(Serverless, "gen_cmd", return_value="cmd")
        npm_install = mocker.patch.object(Serverless, "npm_install")
        run_module_command = mocker.patch(f"{MODULE}.run_module_command")
        obj = Serverless(runway_context, module_root=tmp_path)
        assert (
            obj.sls_package(output_path=output_path, skip_install=skip_install)  # type: ignore
            == output_path
        )
        if skip_install:
            npm_install.assert_not_called()
        else:
            npm_install.assert_called_once_with()
        if output_path:
            gen_cmd.assert_called_once_with(
                "package", args_list=["--package", str(output_path)]
            )
        else:
            gen_cmd.assert_called_once_with("package", args_list=[])
        run_module_command.assert_called_once_with(
            cmd_list=gen_cmd.return_value, env_vars=obj.ctx.env.vars, logger=obj.logger
        )

    @pytest.mark.parametrize(
        "item_path, skip_install", [(None, False), (None, True), ("foo.bar", False)]
    )
    def test_sls_print(
        self,
        item_path: Optional[str],
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        skip_install: bool,
        tmp_path: Path,
    ) -> None:
        """Test sls_print."""
        expected_dict = {"status": "success"}
        mock_check_output = MagicMock(return_value=yaml.safe_dump(expected_dict))
        gen_cmd = mocker.patch.object(
            Serverless, "gen_cmd", MagicMock(return_value=["print"])
        )
        npm_install = mocker.patch.object(Serverless, "npm_install", MagicMock())
        mocker.patch("subprocess.check_output", mock_check_output)
        assert (
            Serverless(runway_context, module_root=tmp_path).sls_print(
                item_path=item_path, skip_install=skip_install
            )
            == expected_dict
        )
        if skip_install:
            npm_install.assert_not_called()
        else:
            npm_install.assert_called_once_with()
        if item_path:
            gen_cmd.assert_called_once_with(
                "print", args_list=["--format", "yaml", "--path", item_path]
            )
        else:
            gen_cmd.assert_called_once_with("print", args_list=["--format", "yaml"])
        mock_check_output.assert_called_once_with(
            ["print"], env={"SLS_DEPRECATION_DISABLE": "*", **runway_context.env.vars}
        )

    @pytest.mark.parametrize("skip_install", [False, True])
    def test_sls_remove(
        self,
        fake_process: FakeProcess,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        skip_install: bool,
        tmp_path: Path,
    ) -> None:
        """Test sls_remove."""
        fake_process.register_subprocess("remove", stdout="success")
        gen_cmd = mocker.patch.object(
            Serverless, "gen_cmd", MagicMock(return_value=["remove"])
        )
        npm_install = mocker.patch.object(Serverless, "npm_install", MagicMock())
        assert not Serverless(runway_context, module_root=tmp_path).sls_remove(
            skip_install=skip_install
        )
        if skip_install:
            npm_install.assert_not_called()
        else:
            npm_install.assert_called_once_with()
        gen_cmd.assert_called_once_with("remove")

    def test_sls_remove_handle_does_not_exist(
        self,
        fake_process: FakeProcess,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test sls_remove."""
        fake_process.register_subprocess(
            "remove",
            stdout=[
                "  Serverless Error ---------------------------------------",
                "",
                "  Stack 'test-stack' does not exist",
                "",
                "  Get Support --------------------------------------------",
                "     Docs:          docs.serverless.com",
                "     Bugs:          github.com/serverless/serverless/issues",
                "     Issues:        forum.serverless.com",
            ],
            returncode=1,
        )
        mocker.patch.object(Serverless, "gen_cmd", MagicMock(return_value=["remove"]))
        mocker.patch.object(Serverless, "npm_install", MagicMock())
        assert not Serverless(runway_context, module_root=tmp_path).sls_remove()

    def test_sls_remove_raise_system_exit(
        self,
        fake_process: FakeProcess,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        tmp_path: Path,
    ) -> None:
        """Test sls_remove."""
        fake_process.register_subprocess(
            "remove",
            stdout=[
                "  Serverless Error ---------------------------------------",
                "",
                "  Some other error",
                "",
                "  Get Support --------------------------------------------",
                "     Docs:          docs.serverless.com",
                "     Bugs:          github.com/serverless/serverless/issues",
                "     Issues:        forum.serverless.com",
            ],
            returncode=1,
        )
        mocker.patch.object(Serverless, "gen_cmd", MagicMock(return_value=["remove"]))
        mocker.patch.object(Serverless, "npm_install", MagicMock())
        with pytest.raises(SystemExit):
            assert not Serverless(runway_context, module_root=tmp_path).sls_remove()


class TestServerlessArtifact:
    """Test ServerlessArtifact."""

    def test___init__(self, runway_context: MockRunwayContext, tmp_path: Path) -> None:
        """Test __init__."""
        config = {"foo": "bar"}
        logger = Mock()
        obj = ServerlessArtifact(
            runway_context,
            config,
            logger=logger,
            package_path=str(tmp_path),
            path=str(tmp_path),
        )
        assert obj.ctx == runway_context
        assert obj.config == config
        assert obj.logger == logger
        assert obj.package_path == tmp_path
        assert obj.path == tmp_path

    @pytest.mark.parametrize(
        "service, service_name",
        [("test-service", "test-service"), ({"name": "test-service"}, "test-service")],
    )
    def test_source_hash(
        self,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        service: Union[Dict[str, Any], str],
        service_name: str,
        tmp_path: Path,
    ) -> None:
        """Test source_hash."""
        get_hash_of_files = mocker.patch(
            f"{MODULE}.get_hash_of_files", Mock(return_value="hash")
        )
        assert ServerlessArtifact(
            runway_context,
            {
                "functions": {
                    "func0": {"handler": "src/func0/handler.entry"},
                    "func1": {"handler": "src/func1/handler.entry"},
                },
                "service": service,
            },
            package_path=tmp_path / "package",
            path=tmp_path,
        ).source_hash == {service_name: get_hash_of_files.return_value}
        get_hash_of_files.assert_called_once_with(
            tmp_path, [{"path": "src/func0"}, {"path": "src/func1"}]
        )

    @pytest.mark.parametrize(
        "service",
        ["test-service", {"name": "test-service"}],
    )
    def test_source_hash_individually(
        self,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
        service: Union[Dict[str, Any], str],
        tmp_path: Path,
    ) -> None:
        """Test source_hash."""
        get_hash_of_files = mocker.patch(
            f"{MODULE}.get_hash_of_files", Mock(side_effect=["hash0", "hash1"])
        )
        assert ServerlessArtifact(
            runway_context,
            {
                "functions": {
                    "func0": {"handler": "src/func0/handler.entry"},
                    "func1": {"handler": "src/func1/handler.entry"},
                },
                "package": {"individually": True},
                "service": service,
            },
            package_path=tmp_path / "package",
            path=tmp_path,
        ).source_hash == {"func0": "hash0", "func1": "hash1"}
        get_hash_of_files.assert_has_calls(
            [
                call(tmp_path / "src/func0"),
                call(tmp_path / "src/func1"),
            ]
        )

    def test_sync_with_s3_download(
        self, mocker: MockerFixture, runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test sync_with_s3."""
        does_s3_object_exist = mocker.patch(
            f"{MODULE}.does_s3_object_exist", return_value=True
        )
        download = mocker.patch(f"{MODULE}.download")
        session = Mock()
        package_path = tmp_path / "package"
        upload = mocker.patch(f"{MODULE}.upload")
        mocker.patch.object(runway_context, "get_session", return_value=session)
        mocker.patch.object(ServerlessArtifact, "source_hash", {"service": "hash"})
        assert not ServerlessArtifact(
            runway_context,
            {},
            package_path=package_path,
            path=tmp_path,
        ).sync_with_s3("test-bucket")
        does_s3_object_exist.assert_called_once_with(
            "test-bucket",
            "hash.zip",
            session=session,
            region=runway_context.env.aws_region,
        )
        download.assert_called_once_with(
            bucket="test-bucket",
            key="hash.zip",
            file_path=str(package_path / "service.zip"),
            session=session,
        )
        upload.assert_not_called()

    def test_sync_with_s3_upload(
        self, mocker: MockerFixture, runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test sync_with_s3."""
        does_s3_object_exist = mocker.patch(
            f"{MODULE}.does_s3_object_exist", return_value=False
        )
        download = mocker.patch(f"{MODULE}.download")
        session = Mock()
        package_path = tmp_path / "package"
        upload = mocker.patch(f"{MODULE}.upload")
        mocker.patch.object(runway_context, "get_session", return_value=session)
        mocker.patch.object(ServerlessArtifact, "source_hash", {"service": "hash"})
        package_path.mkdir()
        (package_path / "service.zip").touch()
        assert not ServerlessArtifact(
            runway_context,
            {},
            package_path=package_path,
            path=tmp_path,
        ).sync_with_s3("test-bucket")
        does_s3_object_exist.assert_called_once_with(
            "test-bucket",
            "hash.zip",
            session=session,
            region=runway_context.env.aws_region,
        )
        download.assert_not_called()
        upload.assert_called_once_with(
            bucket="test-bucket",
            key="hash.zip",
            filename=str(package_path / "service.zip"),
            session=session,
        )

    def test_sync_with_s3_upload_not_exist(
        self, mocker: MockerFixture, runway_context: MockRunwayContext, tmp_path: Path
    ) -> None:
        """Test sync_with_s3."""
        does_s3_object_exist = mocker.patch(
            f"{MODULE}.does_s3_object_exist", return_value=False
        )
        download = mocker.patch(f"{MODULE}.download")
        session = Mock()
        package_path = tmp_path / "package"
        upload = mocker.patch(f"{MODULE}.upload")
        mocker.patch.object(runway_context, "get_session", return_value=session)
        mocker.patch.object(ServerlessArtifact, "source_hash", {"service": "hash"})
        assert not ServerlessArtifact(
            runway_context,
            {},
            package_path=package_path,
            path=tmp_path,
        ).sync_with_s3("test-bucket")
        does_s3_object_exist.assert_called_once_with(
            "test-bucket",
            "hash.zip",
            session=session,
            region=runway_context.env.aws_region,
        )
        download.assert_not_called()
        upload.assert_not_called()


class TestServerlessOptions:
    """Test runway.module.serverless.ServerlessOptions."""

    @pytest.mark.parametrize(
        "args, expected",
        [
            (["--config", "something"], ["--config", "something"]),
            (
                ["--config", "something", "--unknown-arg", "value"],
                ["--config", "something", "--unknown-arg", "value"],
            ),
            (["-c", "something"], ["--config", "something"]),
            (["-u"], ["-u"]),
        ],
    )
    def test_args(self, args: List[str], expected: List[str]) -> None:
        """Test args."""
        obj = ServerlessOptions.parse_obj({"args": args})
        assert obj.args == expected

    @pytest.mark.parametrize(
        "config",
        [
            ({"args": ["--config", "something"]}),
            ({"extend_serverless_yml": {"new_key": "test_value"}}),
            ({"promotezip": {"bucketname": "test-bucket"}}),
            ({"skip_npm_ci": True}),
            (
                {
                    "args": ["--config", "something"],
                    "extend_serverless_yml": {"new_key": "test_value"},
                }
            ),
            (
                {
                    "args": ["--config", "something"],
                    "extend_serverless_yml": {"new_key": "test_value"},
                    "promotezip": {"bucketname": "test-bucket"},
                }
            ),
            (
                {
                    "args": ["--config", "something"],
                    "extend_serverless_yml": {"new_key": "test_value"},
                    "promotezip": {"bucketname": "test-bucket"},
                    "skip_npm_ci": True,
                }
            ),
            (
                {
                    "args": ["--config", "something"],
                    "extend_serverless_yml": {"new_key": "test_value"},
                    "promotezip": {"bucketname": "test-bucket"},
                    "skip_npm_ci": False,
                }
            ),
        ],
    )
    def test_parse(self, config: Dict[str, Any]) -> None:
        """Test parse."""
        obj = ServerlessOptions.parse_obj(config)

        assert obj.args == config.get("args", [])
        assert obj.extend_serverless_yml == config.get(
            "extend_serverless_yml", cast(Dict[str, Any], {})
        )
        if config.get("promotezip"):
            assert obj.promotezip
        else:
            assert not obj.promotezip
        assert obj.promotezip.bucketname == config.get(
            "promotezip", cast(Dict[str, Any], {})
        ).get("bucketname")
        assert obj.skip_npm_ci == config.get("skip_npm_ci", False)

    def test_parse_invalid_promotezip(self) -> None:
        """Test parse with invalid promotezip value."""
        with pytest.raises(ValidationError):
            assert not ServerlessOptions.parse_obj({"promotezip": {"key": "value"}})

    def test_update_args(self) -> None:
        """Test update_args."""
        obj = ServerlessOptions(
            RunwayServerlessModuleOptionsDataModel(
                args=["--config", "something", "--unknown-arg", "value"],
                extend_serverless_yml={},
            )
        )
        assert obj.args == ["--config", "something", "--unknown-arg", "value"]

        obj.update_args("config", "something-else")
        assert obj.args == ["--config", "something-else", "--unknown-arg", "value"]

        with pytest.raises(KeyError):
            obj.update_args("invalid-key", "anything")
