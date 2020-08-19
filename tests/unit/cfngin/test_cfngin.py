"""Tests for runway.cfngin entry point."""
# pylint: disable=no-self-use,protected-access.redefined-outer-name
import shutil

import pytest
from mock import MagicMock, call, patch

from runway.cfngin import CFNgin
from runway.core.components import DeployEnvironment

from ..factories import MockRunwayContext


def copy_fixture(src, dest):
    """Wrap shutil.copy to backport use with Path objects."""
    return shutil.copy(str(src.absolute()), str(dest.absolute()))


def copy_basic_fixtures(cfngin_fixtures, tmp_path):
    """Copy the basic env file and config file to a tmp_path."""
    copy_fixture(
        src=cfngin_fixtures / "envs" / "basic.env", dest=tmp_path / "test-us-east-1.env"
    )
    copy_fixture(
        src=cfngin_fixtures / "configs" / "basic.yml", dest=tmp_path / "basic.yml"
    )


@pytest.fixture(scope="function")
def patch_safehaven(monkeypatch):
    """Patch SafeHaven."""
    mock_haven = MagicMock()
    mock_haven.return_value = mock_haven
    monkeypatch.setattr("runway.cfngin.cfngin.SafeHaven", mock_haven)
    return mock_haven


class TestCFNgin(object):
    """Test runway.cfngin.CFNgin."""

    @staticmethod
    def configure_mock_action_instance(mock_action):
        """Configure a mock action."""
        mock_instance = MagicMock(return_value=None)
        mock_action.return_value = mock_instance
        mock_instance.execute = MagicMock()
        return mock_instance

    @staticmethod
    def get_context(name="test", region="us-east-1"):
        """Create a basic Runway context object."""
        context = MockRunwayContext(
            deploy_environment=DeployEnvironment(explicit_name=name)
        )
        context.env.aws_region = region
        return context

    def test_env_file(self, tmp_path):
        """Test that the correct env file is selected."""
        test_env = tmp_path / "test.env"
        # python2 Path.write_text requires unicode
        test_env.write_text(u"test_value: test")

        # support python < 3.6
        result = CFNgin(ctx=self.get_context(), sys_path=str(tmp_path))
        assert result.env_file.test_value == "test"

        test_us_east_1 = tmp_path / "test-us-east-1.env"
        # python2 Path.write_text requires unicode
        test_us_east_1.write_text(u"test_value: test-us-east-1")

        test_us_west_2 = tmp_path / "test-us-west-2.env"
        # python2 Path.write_text requires unicode
        test_us_west_2.write_text(u"test_value: test-us-west-2")

        lab_ca_central_1 = tmp_path / "lab-ca-central-1.env"
        # python2 Path.write_text requires unicode
        lab_ca_central_1.write_text(u"test_value: lab-ca-central-1")

        # support python < 3.6
        result = CFNgin(ctx=self.get_context(), sys_path=str(tmp_path))
        assert result.env_file.test_value == "test-us-east-1"

        result = CFNgin(
            ctx=self.get_context(region="us-west-2"), sys_path=str(tmp_path)
        )  # support python < 3.6
        assert result.env_file.test_value == "test-us-west-2"

        result = CFNgin(
            ctx=self.get_context(name="lab", region="ca-central-1"),
            sys_path=str(tmp_path),
        )  # support python < 3.6
        assert result.env_file.test_value == "lab-ca-central-1"

    @patch("runway.cfngin.actions.build.Action")
    def test_deploy(self, mock_action, cfngin_fixtures, tmp_path, patch_safehaven):
        """Test deploy with two files & class init."""
        mock_instance = self.configure_mock_action_instance(mock_action)
        copy_basic_fixtures(cfngin_fixtures, tmp_path)
        copy_fixture(
            src=cfngin_fixtures / "configs" / "basic.yml", dest=tmp_path / "basic2.yml"
        )

        context = self.get_context()
        context.env_vars["CI"] = "1"

        cfngin = CFNgin(
            ctx=context,
            parameters={"test_param": "test-param-value"},
            sys_path=str(tmp_path),
        )  # support python < 3.6
        cfngin.deploy()

        assert cfngin.concurrency == 0
        assert not cfngin.interactive
        assert cfngin.parameters.bucket_name == "cfngin-bucket"
        assert cfngin.parameters.environment == "test"
        assert cfngin.parameters.namespace == "test-namespace"
        assert cfngin.parameters.region == "us-east-1"
        assert cfngin.parameters.test_key == "test_value"
        assert cfngin.parameters.test_param == "test-param-value"
        assert cfngin.recreate_failed
        assert cfngin.region == "us-east-1"
        assert cfngin.sys_path == str(tmp_path)
        assert not cfngin.tail

        assert mock_action.call_count == 2
        mock_instance.execute.has_calls(
            [{"concurrency": 0, "tail": False}, {"concurrency": 0, "tail": False}]
        )
        patch_safehaven.assert_has_calls(
            [
                call(
                    environ=context.env_vars,
                    sys_modules_exclude=["awacs", "troposphere"],
                ),
                call.__enter__(),
                call(
                    argv=["stacker", "build", str(tmp_path / "basic.yml")],
                    sys_modules_exclude=["awacs", "troposphere"],
                ),
                call.__enter__(),
                call.__exit__(None, None, None),
                call(
                    argv=["stacker", "build", str(tmp_path / "basic2.yml")],
                    sys_modules_exclude=["awacs", "troposphere"],
                ),
                call.__enter__(),
                call.__exit__(None, None, None),
                call.__exit__(None, None, None),
            ]
        )

    @patch("runway.cfngin.actions.destroy.Action")
    def test_destroy(self, mock_action, cfngin_fixtures, tmp_path, patch_safehaven):
        """Test destroy."""
        mock_instance = self.configure_mock_action_instance(mock_action)
        copy_basic_fixtures(cfngin_fixtures, tmp_path)

        context = self.get_context()
        cfngin = CFNgin(ctx=context, sys_path=str(tmp_path))
        cfngin.destroy()

        mock_action.assert_called_once()
        mock_instance.execute.assert_called_once_with(
            concurrency=0, force=True, tail=False
        )
        patch_safehaven.assert_has_calls(
            [
                call(environ=context.env_vars),
                call.__enter__(),
                call(argv=["stacker", "destroy", str(tmp_path / "basic.yml")]),
                call.__enter__(),
                call.__exit__(None, None, None),
                call.__exit__(None, None, None),
            ]
        )

    def test_load(self, cfngin_fixtures, tmp_path):
        """Test load."""
        copy_basic_fixtures(cfngin_fixtures, tmp_path)
        # support python < 3.6
        cfngin = CFNgin(ctx=self.get_context(), sys_path=str(tmp_path))
        result = cfngin.load(str(tmp_path / "basic.yml"))  # support python < 3.6

        assert not result.bucket_name
        assert result.namespace == "test-namespace"
        assert len(result.get_stacks()) == 1
        assert result.get_stacks()[0].name == "test-stack"

    def test_load_cfn_template(self, caplog, tmp_path):
        """Test load a CFN template."""
        cfn_template = tmp_path / "template.yml"
        cfn_template.write_text(u"test_key: !Ref something")
        cfngin = CFNgin(ctx=self.get_context(), sys_path=str(tmp_path))

        caplog.set_level("ERROR", logger="runway.cfngin")

        with pytest.raises(SystemExit):
            cfngin.load(str(cfn_template))  # support python < 3.6

        assert "appears to be a CloudFormation template" in caplog.text

    @patch("runway.cfngin.actions.diff.Action")
    def test_plan(self, mock_action, cfngin_fixtures, tmp_path, patch_safehaven):
        """Test plan."""
        mock_instance = self.configure_mock_action_instance(mock_action)
        copy_basic_fixtures(cfngin_fixtures, tmp_path)

        context = self.get_context()
        cfngin = CFNgin(ctx=context, sys_path=str(tmp_path))
        cfngin.plan()

        mock_action.assert_called_once()
        mock_instance.execute.assert_called_once_with()
        patch_safehaven.assert_has_calls(
            [
                call(environ=context.env_vars),
                call.__enter__(),
                call(argv=["stacker", "diff", str(tmp_path / "basic.yml")]),
                call.__enter__(),
                call.__exit__(None, None, None),
                call.__exit__(None, None, None),
            ]
        )

    def test_should_skip(self, cfngin_fixtures, tmp_path):
        """Test should_skip."""
        # support python < 3.6
        cfngin = CFNgin(ctx=self.get_context(), sys_path=str(tmp_path))
        del cfngin.env_file  # clear cached value and force load

        assert cfngin.should_skip()
        del cfngin.env_file  # clear cached value and force load
        assert not cfngin.should_skip(force=True)  # does not repopulate env_file

        copy_basic_fixtures(cfngin_fixtures, tmp_path)
        assert not cfngin.should_skip()
        del cfngin.env_file  # clear cached value and force load
        assert not cfngin.should_skip(force=True)  # does not repopulate env_file

        env_region_file = tmp_path / "test-us-east-1.env"
        env_file = tmp_path / "test.env"
        copy_fixture(env_region_file, env_file)
        env_region_file.unlink()
        assert not cfngin.should_skip()
        del cfngin.env_file  # clear cached value and force load
        assert not cfngin.should_skip(force=True)  # does not repopulate env_file

    def test_find_config_files(self, tmp_path):
        """Test find_config_files."""
        bad_path = tmp_path / "bad_path"
        bad_path.mkdir()
        # tmp_path.stem

        good_config_paths = [
            tmp_path / "_t3sT.yaml",
            tmp_path / "_t3sT.yml",
            tmp_path / "01-config.yaml",
            tmp_path / "01-config.yml",
            tmp_path / "TeSt_02.yaml",
            tmp_path / "TeSt_02.yml",
            tmp_path / "test.config.yaml",
            tmp_path / "test.config.yml",
        ]
        bad_config_paths = [
            tmp_path / ".anything.yaml",
            tmp_path / ".gitlab-ci.yml",
            tmp_path / "docker-compose.yml",
            bad_path / "00-invalid.yml",
        ]

        for config_path in good_config_paths + bad_config_paths:
            # python2 Path.write_text requires unicode
            config_path.write_text(u"")

        # support python < 3.6
        result = CFNgin.find_config_files(sys_path=str(tmp_path))
        expected = sorted([str(config_path) for config_path in good_config_paths])
        assert result == expected

        config_01 = tmp_path / "01-config.yml"
        result = CFNgin.find_config_files(
            sys_path=str(config_01)  # support python < 3.6
        )
        assert result == [str(config_01)]  # support python < 3.6

        result = CFNgin.find_config_files()
        assert not result
