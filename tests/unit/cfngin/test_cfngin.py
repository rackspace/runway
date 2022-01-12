"""Tests for runway.cfngin entry point."""
# pylint: disable=no-self-use,redefined-outer-name
from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

import pytest
from mock import Mock, call
from yaml.constructor import ConstructorError

from runway.cfngin.cfngin import CFNgin
from runway.core.components import DeployEnvironment

from ..factories import MockRunwayContext

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import LogCaptureFixture
    from pytest_mock import MockerFixture


def copy_fixture(src: Path, dest: Path) -> Path:
    """Wrap shutil.copy to backport use with Path objects."""
    return shutil.copy(src.absolute(), dest.absolute())


def copy_basic_fixtures(cfngin_fixtures: Path, tmp_path: Path) -> None:
    """Copy the basic env file and config file to a tmp_path."""
    copy_fixture(
        src=cfngin_fixtures / "envs" / "basic.env", dest=tmp_path / "test-us-east-1.env"
    )
    copy_fixture(
        src=cfngin_fixtures / "configs" / "basic.yml", dest=tmp_path / "basic.yml"
    )


@pytest.fixture(scope="function")
def patch_safehaven(mocker: MockerFixture) -> Mock:
    """Patch SafeHaven."""
    mock_haven = mocker.patch("runway.cfngin.cfngin.SafeHaven")
    mock_haven.return_value = mock_haven
    return mock_haven


class TestCFNgin:
    """Test runway.cfngin.CFNgin."""

    @staticmethod
    def configure_mock_action_instance(mock_action: Mock) -> Mock:
        """Configure a mock action."""
        mock_instance = Mock(return_value=None)
        mock_action.return_value = mock_instance
        mock_instance.execute = Mock()
        return mock_instance

    @staticmethod
    def get_context(name: str = "test", region: str = "us-east-1") -> MockRunwayContext:
        """Create a basic Runway context object."""
        context = MockRunwayContext(
            deploy_environment=DeployEnvironment(explicit_name=name)
        )
        context.env.aws_region = region
        return context

    def test_env_file(self, tmp_path: Path) -> None:
        """Test that the correct env file is selected."""
        test_env = tmp_path / "test.env"
        test_env.write_text("test_value: test")

        result = CFNgin(ctx=self.get_context(), sys_path=tmp_path)
        assert result.env_file["test_value"] == "test"

        test_us_east_1 = tmp_path / "test-us-east-1.env"
        test_us_east_1.write_text("test_value: test-us-east-1")

        test_us_west_2 = tmp_path / "test-us-west-2.env"
        test_us_west_2.write_text("test_value: test-us-west-2")

        lab_ca_central_1 = tmp_path / "lab-ca-central-1.env"
        lab_ca_central_1.write_text("test_value: lab-ca-central-1")

        result = CFNgin(ctx=self.get_context(), sys_path=tmp_path)
        assert result.env_file["test_value"] == "test-us-east-1"

        result = CFNgin(ctx=self.get_context(region="us-west-2"), sys_path=tmp_path)
        assert result.env_file["test_value"] == "test-us-west-2"

        result = CFNgin(
            ctx=self.get_context(name="lab", region="ca-central-1"), sys_path=tmp_path
        )
        assert result.env_file["test_value"] == "lab-ca-central-1"

    def test_deploy(
        self,
        cfngin_fixtures: Path,
        mocker: MockerFixture,
        tmp_path: Path,
        patch_safehaven: Mock,
    ) -> None:
        """Test deploy with two files & class init."""
        mock_action = mocker.patch("runway.cfngin.actions.deploy.Action", Mock())
        mock_instance = self.configure_mock_action_instance(mock_action)
        copy_basic_fixtures(cfngin_fixtures, tmp_path)
        copy_fixture(
            src=cfngin_fixtures / "configs" / "basic.yml", dest=tmp_path / "basic2.yml"
        )

        context = self.get_context()
        context.env.vars["CI"] = "1"

        cfngin = CFNgin(
            ctx=context,
            parameters={"test_param": "test-param-value"},
            sys_path=tmp_path,
        )
        cfngin.deploy()

        assert cfngin.concurrency == 0
        assert not cfngin.interactive
        assert cfngin.parameters["bucket_name"] == "cfngin-bucket"
        assert cfngin.parameters["environment"] == "test"
        assert cfngin.parameters["namespace"] == "test-namespace"
        assert cfngin.parameters["region"] == "us-east-1"
        assert cfngin.parameters["test_key"] == "test_value"
        assert cfngin.parameters["test_param"] == "test-param-value"
        assert cfngin.recreate_failed
        assert cfngin.region == "us-east-1"
        assert cfngin.sys_path == tmp_path
        assert not cfngin.tail

        assert mock_action.call_count == 2
        mock_instance.execute.has_calls(
            [{"concurrency": 0, "tail": False}, {"concurrency": 0, "tail": False}]
        )
        patch_safehaven.assert_has_calls(
            [
                call(
                    environ=context.env.vars,
                    sys_modules_exclude=["awacs", "troposphere"],
                ),
                call.__enter__(),
                call(sys_modules_exclude=["awacs", "troposphere"]),
                call.__enter__(),
                call.__exit__(None, None, None),
                call(sys_modules_exclude=["awacs", "troposphere"]),
                call.__enter__(),
                call.__exit__(None, None, None),
                call.__exit__(None, None, None),
            ]
        )

    def test_deploy_skip(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        patch_safehaven: Mock,
    ) -> None:
        """Test deploy skip."""
        should_skip = mocker.patch.object(CFNgin, "should_skip", return_value=True)
        cfngin = CFNgin(
            ctx=self.get_context(),
            sys_path=tmp_path,
        )
        cfngin.deploy()
        should_skip.assert_called_once_with(False)
        patch_safehaven.assert_not_called()

    def test_destroy(
        self,
        cfngin_fixtures: Path,
        mocker: MockerFixture,
        tmp_path: Path,
        patch_safehaven: Mock,
    ) -> None:
        """Test destroy."""
        mock_action = mocker.patch("runway.cfngin.actions.destroy.Action", Mock())
        mock_instance = self.configure_mock_action_instance(mock_action)
        copy_basic_fixtures(cfngin_fixtures, tmp_path)

        context = self.get_context()
        cfngin = CFNgin(ctx=context, sys_path=tmp_path)
        cfngin.destroy()

        mock_action.assert_called_once()
        mock_instance.execute.assert_called_once_with(
            concurrency=0, force=True, tail=False
        )
        patch_safehaven.assert_has_calls(
            [
                call(environ=context.env.vars),
                call.__enter__(),
                call(),
                call.__enter__(),
                call.__exit__(None, None, None),
                call.__exit__(None, None, None),
            ]
        )

    def test_destroy_skip(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        patch_safehaven: Mock,
    ) -> None:
        """Test destroy skip."""
        should_skip = mocker.patch.object(CFNgin, "should_skip", return_value=True)
        cfngin = CFNgin(
            ctx=self.get_context(),
            sys_path=tmp_path,
        )
        cfngin.destroy()
        should_skip.assert_called_once_with(False)
        patch_safehaven.assert_not_called()

    def test_init(
        self,
        cfngin_fixtures: Path,
        mocker: MockerFixture,
        patch_safehaven: Mock,
        tmp_path: Path,
    ) -> None:
        """Test init."""
        mock_action = mocker.patch("runway.cfngin.actions.init.Action", Mock())
        mock_instance = self.configure_mock_action_instance(mock_action)
        copy_basic_fixtures(cfngin_fixtures, tmp_path)

        context = self.get_context()
        cfngin = CFNgin(ctx=context, sys_path=tmp_path)
        cfngin.init()

        mock_action.assert_called_once()
        mock_instance.execute.assert_called_once_with(concurrency=0, tail=False)
        patch_safehaven.assert_has_calls(
            [
                call(
                    environ=context.env.vars,
                    sys_modules_exclude=["awacs", "troposphere"],
                ),
                call.__enter__(),
                call(sys_modules_exclude=["awacs", "troposphere"]),
                call.__enter__(),
                call.__exit__(None, None, None),
                call.__exit__(None, None, None),
            ]
        )

    def test_init_skip(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        patch_safehaven: Mock,
    ) -> None:
        """Test init skip."""
        should_skip = mocker.patch.object(CFNgin, "should_skip", return_value=True)
        cfngin = CFNgin(
            ctx=self.get_context(),
            sys_path=tmp_path,
        )
        cfngin.init()
        should_skip.assert_called_once_with(False)
        patch_safehaven.assert_not_called()

    def test_load(self, cfngin_fixtures: Path, tmp_path: Path) -> None:
        """Test load."""
        copy_basic_fixtures(cfngin_fixtures, tmp_path)
        cfngin = CFNgin(ctx=self.get_context(), sys_path=tmp_path)
        result = cfngin.load(tmp_path / "basic.yml")

        assert not result.bucket_name
        assert result.namespace == "test-namespace"
        assert len(result.stacks) == 1
        assert result.stacks[0].name == "test-stack"

    def test_load_cfn_template(self, caplog: LogCaptureFixture, tmp_path: Path) -> None:
        """Test load a CFN template."""
        cfn_template = tmp_path / "template.yml"
        cfn_template.write_text("test_key: !Ref something")
        cfngin = CFNgin(ctx=self.get_context(), sys_path=tmp_path)

        caplog.set_level("ERROR", logger="runway.cfngin")

        with pytest.raises(SystemExit):
            cfngin.load(cfn_template)

        assert "appears to be a CloudFormation template" in caplog.text

    def test_load_raise_constructor_error(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """Test load raise ConstructorError."""
        config = Mock(load=Mock(side_effect=ConstructorError(problem="something else")))
        get_config = mocker.patch.object(CFNgin, "_get_config", return_value=config)
        with pytest.raises(ConstructorError, match="something else"):
            assert CFNgin(ctx=self.get_context(), sys_path=tmp_path).load(tmp_path)
        get_config.assert_called_once_with(tmp_path)

    def test_plan(
        self,
        cfngin_fixtures: Path,
        mocker: MockerFixture,
        tmp_path: Path,
        patch_safehaven: Mock,
    ) -> None:
        """Test plan."""
        mock_action = mocker.patch("runway.cfngin.actions.diff.Action", Mock())
        mock_instance = self.configure_mock_action_instance(mock_action)
        copy_basic_fixtures(cfngin_fixtures, tmp_path)

        context = self.get_context()
        cfngin = CFNgin(ctx=context, sys_path=tmp_path)
        cfngin.plan()

        mock_action.assert_called_once()
        mock_instance.execute.assert_called_once_with()
        patch_safehaven.assert_has_calls(
            [
                call(environ=context.env.vars),
                call.__enter__(),
                call(),
                call.__enter__(),
                call.__exit__(None, None, None),
                call.__exit__(None, None, None),
            ]
        )

    def test_plan_skip(
        self,
        mocker: MockerFixture,
        tmp_path: Path,
        patch_safehaven: Mock,
    ) -> None:
        """Test plan skip."""
        should_skip = mocker.patch.object(CFNgin, "should_skip", return_value=True)
        cfngin = CFNgin(
            ctx=self.get_context(),
            sys_path=tmp_path,
        )
        cfngin.plan()
        should_skip.assert_called_once_with(False)
        patch_safehaven.assert_not_called()

    def test_should_skip(self, cfngin_fixtures: Path, tmp_path: Path) -> None:
        """Test should_skip."""
        cfngin = CFNgin(ctx=self.get_context(), sys_path=tmp_path)
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

    def test_find_config_files(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test find_config_files."""
        mock_config = mocker.patch("runway.cfngin.cfngin.CfnginConfig", Mock())
        CFNgin.find_config_files(sys_path=tmp_path, exclude=["file"])
        mock_config.find_config_file.assert_called_once_with(tmp_path, exclude=["file"])
