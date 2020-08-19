"""Test runway.module.serverless."""
# pylint: disable=no-self-use,unused-argument
import logging
import subprocess
import sys

import pytest
import yaml
from mock import ANY, MagicMock, patch

from runway.module.serverless import Serverless, ServerlessOptions, gen_sls_config_files

from ..factories import MockProcess


@pytest.mark.usefixtures("patch_module_npm")
class TestServerless(object):
    """Test runway.module.serverless.Serverless."""

    def test_cli_args(self, runway_context):
        """Test cli_args."""
        obj = Serverless(runway_context, "./tests")

        assert obj.cli_args == [
            "--region",
            runway_context.env_region,
            "--stage",
            runway_context.env_name,
        ]

        runway_context.env_vars["DEBUG"] = "1"
        assert obj.cli_args == [
            "--region",
            runway_context.env_region,
            "--stage",
            runway_context.env_name,
            "--verbose",
        ]

    def test_deploy(self, monkeypatch, runway_context):
        """Test deploy."""
        # pylint: disable=no-member
        monkeypatch.setattr(Serverless, "extend_serverless_yml", MagicMock())
        monkeypatch.setattr(Serverless, "sls_deploy", MagicMock())
        obj = Serverless(runway_context, "./tests")

        monkeypatch.setattr(Serverless, "skip", True)
        assert not obj.deploy()
        obj.extend_serverless_yml.assert_not_called()
        obj.sls_deploy.assert_not_called()

        monkeypatch.setattr(Serverless, "skip", False)
        monkeypatch.setattr(obj.options, "extend_serverless_yml", True)
        assert not obj.deploy()
        obj.extend_serverless_yml.assert_called_once_with(obj.sls_deploy)
        obj.sls_deploy.assert_not_called()

        monkeypatch.setattr(obj.options, "extend_serverless_yml", False)
        assert not obj.deploy()
        obj.extend_serverless_yml.assert_called_once()
        obj.sls_deploy.assert_called_once_with()

    def test_destroy(self, monkeypatch, runway_context):
        """Test destroy."""
        # pylint: disable=no-member
        monkeypatch.setattr(Serverless, "extend_serverless_yml", MagicMock())
        monkeypatch.setattr(Serverless, "sls_remove", MagicMock())
        obj = Serverless(runway_context, "./tests")

        monkeypatch.setattr(Serverless, "skip", True)
        assert not obj.destroy()
        obj.extend_serverless_yml.assert_not_called()
        obj.sls_remove.assert_not_called()

        monkeypatch.setattr(Serverless, "skip", False)
        monkeypatch.setattr(obj.options, "extend_serverless_yml", True)
        assert not obj.destroy()
        obj.extend_serverless_yml.assert_called_once_with(obj.sls_remove)
        obj.sls_remove.assert_not_called()

        monkeypatch.setattr(obj.options, "extend_serverless_yml", False)
        assert not obj.destroy()
        obj.extend_serverless_yml.assert_called_once()
        obj.sls_remove.assert_called_once_with()

    def test_env_file(self, runway_context, tmp_path):
        """Test env_file.

        Testing the precedence of each path, create the files in order from
        lowerst to highest. After creating the file, the property's value
        is checked then cleared since the value is cached after the first
        time it is resolved.

        """
        env_dir = tmp_path / "env"
        env_dir.mkdir()
        obj = Serverless(runway_context, tmp_path)
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

    @patch("runway.module.serverless.merge_dicts")
    def test_extend_serverless_yml(
        self, mock_merge, caplog, monkeypatch, runway_context, tmp_path
    ):
        """Test extend_serverless_yml."""
        # pylint: disable=no-member
        caplog.set_level(logging.DEBUG, logger="runway")
        mock_func = MagicMock()
        mock_merge.return_value = {"key": "val"}
        monkeypatch.setattr(Serverless, "npm_install", MagicMock())
        monkeypatch.setattr(Serverless, "sls_print", MagicMock(return_value="original"))
        monkeypatch.setattr(ServerlessOptions, "update_args", MagicMock())

        options = {"extend_serverless_yml": {"new-key": "val"}}
        obj = Serverless(runway_context, tmp_path, options={"options": options})

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
        monkeypatch.setattr(
            "{}.Path.unlink".format(
                "pathlib" if sys.version_info.major == 3 else "pathlib2"
            ),
            MagicMock(side_effect=OSError("test OSError")),
        )
        assert not obj.extend_serverless_yml(mock_func)
        assert (
            "{}:encountered an error when trying to delete the "
            "temporary Serverless config".format(tmp_path.name) in caplog.messages
        )

    @patch("runway.module.serverless.generate_node_command")
    @pytest.mark.parametrize("command", [("deploy"), ("remove"), ("print")])
    def test_gen_cmd(self, mock_cmd, command, monkeypatch, runway_context, tmp_path):
        """Test gen_cmd."""
        # pylint: disable=no-member
        monkeypatch.setattr(runway_context, "no_color", False)
        mock_cmd.return_value = ["success"]
        obj = Serverless(
            runway_context, tmp_path, {"options": {"args": ["--config", "test"]}}
        )
        expected_opts = [
            command,
            "--region",
            runway_context.env_region,
            "--stage",
            runway_context.env_name,
            "--config",
            "test",
            "--extra-arg",
        ]

        assert obj.gen_cmd(command, args_list=["--extra-arg"]) == ["success"]
        mock_cmd.assert_called_once_with(
            command="sls", command_opts=expected_opts, logger=obj.logger, path=tmp_path
        )
        mock_cmd.reset_mock()

        obj.context.env_vars["CI"] = "1"
        monkeypatch.setattr(runway_context, "no_color", True)
        expected_opts.append("--no-color")
        if command not in ["remove", "print"]:
            expected_opts.append("--conceal")
        assert obj.gen_cmd(command, args_list=["--extra-arg"]) == ["success"]
        mock_cmd.assert_called_once_with(
            command="sls", command_opts=expected_opts, logger=obj.logger, path=tmp_path
        )

    def test_init(self, caplog, runway_context):
        """Test init and the attributes set in init."""
        caplog.set_level(logging.ERROR, logger="runway")
        obj = Serverless(runway_context, "./tests", {"options": {"skip_npm_ci": True}})
        assert isinstance(obj.options, ServerlessOptions)
        assert obj.region == runway_context.env_region
        assert obj.stage == runway_context.env_name

        with pytest.raises(SystemExit):
            assert not Serverless(
                runway_context,
                "./tests",
                {"options": {"promotezip": {"invalid": "value"}}},
            )
        assert ["tests:error encountered while parsing options"] == caplog.messages

    def test_plan(self, caplog, runway_context):
        """Test plan."""
        caplog.set_level(logging.INFO, logger="runway")
        obj = Serverless(runway_context, "./tests")

        assert not obj.plan()
        assert ["tests:plan not currently supported for Serverless"] == caplog.messages

    def test_skip(self, caplog, monkeypatch, runway_context, tmp_path):
        """Test skip."""
        caplog.set_level(logging.INFO, logger="runway")
        obj = Serverless(runway_context, tmp_path)
        monkeypatch.setattr(obj, "package_json_missing", lambda: True)
        monkeypatch.setattr(obj, "env_file", False)

        assert obj.skip
        assert [
            '{}:skipped; package.json with "serverless" in devDependencies'
            " is required for this module type".format(tmp_path.name)
        ] == caplog.messages
        caplog.clear()

        monkeypatch.setattr(obj, "package_json_missing", lambda: False)
        assert obj.skip
        assert [
            "{}:skipped; config file for this stage/region not found"
            " -- looking for one of: {}".format(
                tmp_path.name, ", ".join(gen_sls_config_files(obj.stage, obj.region))
            )
        ] == caplog.messages
        caplog.clear()

        obj.environments = True
        assert not obj.skip
        obj.environments = False

        obj.parameters = True
        assert not obj.skip
        obj.parameters = False

        obj.env_file = True
        assert not obj.skip

    @patch("runway.module.serverless.deploy_package")
    @patch("runway.module.serverless.run_module_command")
    def test_sls_deploy(
        self, mock_run, mock_deploy, monkeypatch, runway_context, tmp_path
    ):
        """Test sls_deploy."""
        # pylint: disable=no-member
        monkeypatch.setattr(runway_context, "no_color", False)
        monkeypatch.setattr(Serverless, "gen_cmd", MagicMock(return_value=["deploy"]))
        monkeypatch.setattr(Serverless, "npm_install", MagicMock())
        obj = Serverless(
            runway_context,
            tmp_path,
            options={"options": {"args": ["--config", "test.yml"]}},
        )

        assert not obj.sls_deploy()
        obj.npm_install.assert_called_once()
        obj.gen_cmd.assert_called_once_with("deploy")
        mock_run.assert_called_once_with(
            cmd_list=["deploy"], env_vars=runway_context.env_vars, logger=obj.logger
        )

        obj.options.promotezip["bucketname"] = "test-bucket"
        assert not obj.sls_deploy(skip_install=True)
        obj.npm_install.assert_called_once()
        mock_deploy.assert_called_once_with(
            [
                "deploy",
                "--region",
                runway_context.env_region,
                "--stage",
                runway_context.env_name,
                "--config",
                "test.yml",
            ],
            "test-bucket",
            runway_context,
            str(tmp_path),
            obj.logger,
        )
        mock_run.assert_called_once()

        monkeypatch.setattr(runway_context, "no_color", True)
        assert not obj.sls_deploy(skip_install=True)
        mock_deploy.assert_called_with(
            [
                "deploy",
                "--region",
                runway_context.env_region,
                "--stage",
                runway_context.env_name,
                "--config",
                "test.yml",
                "--no-color",
            ],
            "test-bucket",
            runway_context,
            str(tmp_path),
            obj.logger,
        )

    def test_sls_print(self, monkeypatch, runway_context):
        """Test sls_print."""
        # pylint: disable=no-member
        expected_dict = {"status": "success"}
        mock_check_output = MagicMock(return_value=yaml.safe_dump(expected_dict))
        monkeypatch.setattr(Serverless, "gen_cmd", MagicMock(return_value=["print"]))
        monkeypatch.setattr(Serverless, "npm_install", MagicMock())
        monkeypatch.setattr("subprocess.check_output", mock_check_output)
        obj = Serverless(runway_context, "./tests")

        assert obj.sls_print() == expected_dict
        obj.npm_install.assert_called_once()
        mock_check_output.assert_called_once_with(
            ["print"], env=runway_context.env_vars
        )
        obj.gen_cmd.assert_called_once_with("print", args_list=["--format", "yaml"])
        obj.gen_cmd.reset_mock()

        assert (
            obj.sls_print(item_path="something.status", skip_install=True)
            == expected_dict
        )
        obj.npm_install.assert_called_once()
        obj.gen_cmd.assert_called_once_with(
            "print", args_list=["--format", "yaml", "--path", "something.status"]
        )

    def test_sls_remove(self, monkeypatch, runway_context):
        """Test sls_remove."""
        # pylint: disable=no-member
        # TODO use pytest-subprocess for when dropping python 2
        sls_error = [
            "  Serverless Error ---------------------------------------",
            "",
            "  Stack 'test-stack' does not exist",
            "",
            "  Get Support --------------------------------------------",
            "     Docs:          docs.serverless.com",
            "     Bugs:          github.com/serverless/serverless/issues",
            "     Issues:        forum.serverless.com",
        ]
        mock_popen = MagicMock(return_value=MockProcess(returncode=0, stdout="success"))
        monkeypatch.setattr("subprocess.Popen", mock_popen)
        monkeypatch.setattr(Serverless, "gen_cmd", MagicMock(return_value=["remove"]))
        monkeypatch.setattr(Serverless, "npm_install", MagicMock())

        obj = Serverless(runway_context, "./tests")
        assert not obj.sls_remove()
        obj.npm_install.assert_called_once()
        obj.gen_cmd.assert_called_once_with("remove")
        mock_popen.assert_called_once_with(
            ["remove"],
            bufsize=1,
            env=runway_context.env_vars,
            stdout=subprocess.PIPE,
            universal_newlines=True,
        )
        mock_popen.return_value.wait.assert_called_once()

        mock_popen = MagicMock(return_value=MockProcess(returncode=1, stdout=sls_error))

        monkeypatch.setattr("subprocess.Popen", mock_popen)
        assert not obj.sls_remove(skip_install=True)
        obj.npm_install.assert_called_once()
        mock_popen.return_value.wait.assert_called_once()

        sls_error[2] = "  Some other error"
        mock_popen = MagicMock(return_value=MockProcess(returncode=1, stdout=sls_error))
        monkeypatch.setattr("subprocess.Popen", mock_popen)
        with pytest.raises(SystemExit):
            assert not obj.sls_remove()
        mock_popen.return_value.wait.assert_called_once()


class TestServerlessOptions(object):
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
    def test_args(self, args, expected):
        """Test args."""
        obj = ServerlessOptions(args=args, extend_serverless_yml={}, promotezip={})
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
    def test_parse(self, config):
        """Test parse."""
        obj = ServerlessOptions.parse(**config)

        assert obj.args == config.get("args", [])
        assert obj.extend_serverless_yml == config.get("extend_serverless_yml", {})
        assert obj.promotezip == config.get("promotezip", {})
        assert obj.skip_npm_ci == config.get("skip_npm_ci", False)

    def test_parse_invalid_promotezip(self):
        """Test parse with invalid promotezip value."""
        with pytest.raises(ValueError):
            assert not ServerlessOptions.parse(promotezip={"key": "value"})

    def test_update_args(self):
        """Test update_args."""
        obj = ServerlessOptions(
            args=["--config", "something", "--unknown-arg", "value"],
            extend_serverless_yml={},
            promotezip={},
        )
        assert obj.args == ["--config", "something", "--unknown-arg", "value"]

        obj.update_args("config", "something-else")
        assert obj.args == ["--config", "something-else", "--unknown-arg", "value"]

        with pytest.raises(KeyError):
            obj.update_args("invalid-key", "anything")
