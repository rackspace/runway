"""Test runway.context._runway."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest

from runway.context._runway import RunwayContext
from runway.context.sys_info import OsInfo
from runway.core.components import DeployEnvironment

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

MODULE = "runway.context._runway"


class TestRunwayContext:
    """Test runway.context._runway.RunwayContext."""

    env = DeployEnvironment(explicit_name="test")

    def test_copy(self, mocker: MockerFixture) -> None:
        """Test copy."""
        mocker.patch.object(RunwayContext, "_inject_profile_credentials")
        mock_copy = mocker.patch.object(self.env, "copy", return_value="new")
        obj = RunwayContext(command="test", deploy_environment=self.env)
        obj_copy = obj.copy()

        assert obj_copy != obj
        assert obj_copy.command == obj_copy.command
        assert obj_copy.env == "new"
        mock_copy.assert_called_once_with()

    def test_echo_detected_environment(self, mocker: MockerFixture) -> None:
        """Test echo_detected_environment."""
        mock_log_name = mocker.patch.object(self.env, "log_name")
        obj = RunwayContext(deploy_environment=self.env)
        obj.echo_detected_environment()
        mock_log_name.assert_called_once_with()

    def test_init(self, mocker: MockerFixture) -> None:
        """Test init."""
        mock_inject = mocker.patch.object(RunwayContext, "_inject_profile_credentials")
        obj = RunwayContext(command="test", deploy_environment=self.env)
        assert obj.command == "test"
        assert obj.env == self.env
        assert obj.logger
        mock_inject.assert_called_once_with()

    def test_init_no_args(self, mocker: MockerFixture) -> None:
        """Test init process with no args."""
        mock_env = mocker.patch(f"{MODULE}.DeployEnvironment")
        mock_inject = mocker.patch.object(RunwayContext, "_inject_profile_credentials")

        obj = RunwayContext()
        assert obj.command is None
        mock_env.assert_called_once_with()
        assert obj.env == mock_env.return_value
        assert obj.logger
        mock_inject.assert_called_once_with()

    @pytest.mark.parametrize(
        "colorize, isatty, expected",
        [
            (None, True, False),
            (None, False, True),
            (True, False, False),
            (False, True, True),
            ("true", False, False),
            ("false", True, True),
            (ValueError, True, False),
            (ValueError, False, True),
        ],
    )
    def test_no_color(
        self, colorize: Any, expected: bool, isatty: bool, mocker: MockerFixture
    ) -> None:
        """Test no_color."""
        mocker.patch(f"{MODULE}.sys.stdout", isatty=MagicMock(return_value=isatty))
        mocker.patch.object(self.env, "vars", {"RUNWAY_COLORIZE": colorize})
        assert RunwayContext(deploy_environment=self.env).no_color is expected

    def test_no_color_value_error(self, mocker: MockerFixture) -> None:
        """Test no_color with a ValueError."""
        mocker.patch(f"{MODULE}.sys.stdout", isatty=MagicMock(return_value=True))
        mocker.patch.object(self.env, "vars", {"RUNWAY_COLORIZE": "invalid"})
        assert RunwayContext(deploy_environment=self.env).no_color

    def test_use_concurrent_not_posix(self, mocker: MockerFixture) -> None:
        """Test use_concurrent."""
        mocker.patch.object(OsInfo, "is_posix", False)
        mocker.patch.object(self.env, "ci", False)
        assert not RunwayContext(deploy_environment=self.env).use_concurrent
        mocker.patch.object(self.env, "ci", True)
        assert not RunwayContext(deploy_environment=self.env).use_concurrent

    def test_use_concurrent_posix(self, mocker: MockerFixture) -> None:
        """Test use_concurrent."""
        mocker.patch.object(OsInfo, "is_posix", True)
        mocker.patch.object(self.env, "ci", False)
        assert not RunwayContext(deploy_environment=self.env).use_concurrent
        mocker.patch.object(self.env, "ci", True)
        assert RunwayContext(deploy_environment=self.env).use_concurrent
