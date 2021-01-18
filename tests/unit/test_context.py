"""Tests for context module."""
# pylint: disable=protected-access,no-self-use
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import pytest
from mock import MagicMock, patch

from runway.context import Context

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

LOGGER = logging.getLogger("runway")
MODULE = "runway.context"

TEST_CREDENTIALS = {
    "AWS_ACCESS_KEY_ID": "foo",
    "AWS_SECRET_ACCESS_KEY": "bar",
    "AWS_SESSION_TOKEN": "foobar",
}


class TestContext:
    """Test Context class."""

    def test_boto3_credentials(self, mocker: MockerFixture) -> None:
        """Test boto3_credentials."""
        mocker.patch.object(Context, "current_aws_creds", TEST_CREDENTIALS)
        ctx = Context()

        assert ctx.boto3_credentials == {
            key.lower(): value for key, value in TEST_CREDENTIALS.items()
        }

    def test_current_aws_creds(self) -> None:
        """Test current_aws_creds."""
        mock_env = MagicMock()
        mock_env.aws_credentials = TEST_CREDENTIALS
        ctx = Context(deploy_environment=mock_env)
        assert ctx.current_aws_creds == TEST_CREDENTIALS

    def test_env_name(self) -> None:
        """Test env_name."""
        mock_env = MagicMock()
        mock_env.name = "test"
        ctx = Context(deploy_environment=mock_env)
        assert ctx.env_name == "test"

    def test_env_region(self) -> None:
        """Test env_region."""
        mock_env = MagicMock()
        mock_env.aws_region = "us-east-1"
        ctx = Context(deploy_environment=mock_env)
        assert ctx.env_region == "us-east-1"

        ctx.env_region = "us-west-2"
        assert ctx.env_region == "us-west-2"
        assert mock_env.aws_region == "us-west-2"

    def test_env_root(self, tmp_path: Path) -> None:
        """Test env_root."""
        mock_env = MagicMock()
        mock_env.root_dir = tmp_path
        ctx = Context(deploy_environment=mock_env)
        assert ctx.env_root == str(tmp_path)

    def test_env_vars(self) -> None:
        """Test env_vars."""
        mock_env = MagicMock()
        mock_env.vars = {"test-key": "val"}
        ctx = Context(deploy_environment=mock_env)
        assert ctx.env_vars == {"test-key": "val"}

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
    @patch("runway.context.sys.stdout")
    def test_no_color(
        self, mock_stdout: MagicMock, colorize: Any, isatty: bool, expected: bool
    ) -> Any:
        """Test no_color."""
        mock_stdout.isatty.return_value = isatty
        mock_env = MagicMock()
        mock_env.vars = {}
        if colorize is not None:
            mock_env.vars["RUNWAY_COLORIZE"] = colorize
        ctx = Context(deploy_environment=mock_env)
        assert ctx.no_color == expected

    @patch("runway.context.sys.stdout")
    def test_no_color_value_error(self, mock_stdout: MagicMock) -> None:
        """Test no_color with a ValueError."""
        mock_stdout.isatty.return_value = True
        mock_env = MagicMock()
        mock_env.vars = {"RUNWAY_COLORIZE": "invalid"}
        ctx = Context(deploy_environment=mock_env)
        assert not ctx.no_color

    def test_is_interactive(self) -> None:
        """Test is_interactive."""
        mock_env = MagicMock()
        mock_env.ci = False
        ctx = Context(deploy_environment=mock_env)
        assert ctx.is_interactive

        mock_env.ci = True
        assert not ctx.is_interactive

    def test_is_noninteractive(self) -> None:
        """Test is_noninteractive."""
        mock_env = MagicMock()
        mock_env.ci = False
        ctx = Context(deploy_environment=mock_env)
        assert not ctx.is_noninteractive

        mock_env.ci = True
        assert ctx.is_noninteractive

    def test_use_concurrent(self) -> None:
        """Test use_concurrent."""
        mock_env = MagicMock()
        mock_env.ci = False
        mock_env_ci = MagicMock()
        mock_env_ci.ci = True
        ctx = Context(deploy_environment=mock_env)
        ctx_ci = Context(deploy_environment=mock_env_ci)

        assert not ctx.use_concurrent
        assert ctx_ci.use_concurrent

    @patch(MODULE + ".DeployEnvironment")
    def test_copy(self, mock_env: MagicMock) -> None:
        """Test copy."""
        mock_env.copy.return_value = mock_env
        obj = Context(command="test", deploy_environment=mock_env)
        obj_copy = obj.copy()

        assert obj_copy != obj
        assert obj_copy.command == obj.command
        assert obj_copy.env == mock_env
        mock_env.copy.assert_called_with()

    def test_echo_detected_environment(self) -> None:
        """Test echo_detected_environment."""
        mock_env = MagicMock()
        obj = Context(deploy_environment=mock_env)
        assert not obj.echo_detected_environment()
        mock_env.log_name.assert_called_once_with()

    def test_get_session(self, mocker: MockerFixture) -> None:
        """Test get_session."""
        mock_get_session = mocker.patch(f"{MODULE}.get_session")
        mock_env = MagicMock()
        mock_env.aws_region = "us-east-1"
        mocker.patch.object(Context, "boto3_credentials", {})
        obj = Context(deploy_environment=mock_env)
        assert obj.get_session()
        mock_get_session.assert_called_once_with(region=mock_env.aws_region)

    def test_get_session_args(self, mocker: MockerFixture) -> None:
        """Test get_session with args."""
        mock_get_session = mocker.patch(f"{MODULE}.get_session")
        mock_env = MagicMock()
        mock_env.aws_region = "us-east-1"
        mocker.patch.object(Context, "boto3_credentials", {})
        obj = Context(deploy_environment=mock_env)
        assert obj.get_session(region="us-west-2", profile="something")
        mock_get_session.assert_called_once_with(
            region="us-west-2", profile="something"
        )

    def test_get_session_env_creds(self, mocker: MockerFixture) -> None:
        """Test get_session with env creds."""
        mock_get_session = mocker.patch(f"{MODULE}.get_session")
        creds = {
            "aws_access_key_id": "test-key",
            "aws_secret_access_key": "test-secret",
            "aws_session_token": "test-token",
        }
        mock_env = MagicMock()
        mock_env.aws_region = "us-east-1"
        mocker.patch.object(Context, "boto3_credentials", creds)
        obj = Context(deploy_environment=mock_env)
        assert obj.get_session()
        mock_get_session.assert_called_once()
        call_kwargs = mock_get_session.call_args.kwargs
        assert call_kwargs.pop("access_key") == creds["aws_access_key_id"]
        assert call_kwargs.pop("region") == mock_env.aws_region
        assert call_kwargs.pop("secret_key") == creds["aws_secret_access_key"]
        assert call_kwargs.pop("session_token") == creds["aws_session_token"]
        assert not call_kwargs

    def test_init_from_deploy_environment(self, mocker: MockerFixture) -> None:
        """Test init process with deploy environment."""
        mock_env = MagicMock()
        mock_env.debug = "success"
        mock_inject = mocker.patch.object(
            Context, "_Context__inject_profile_credentials"
        )

        obj = Context(command="test", deploy_environment=mock_env)
        assert obj.command == "test"
        assert obj.env == mock_env
        assert obj.debug == "success"
        mock_inject.assert_called_once_with()

    def test_init_no_args(self, mocker: MockerFixture) -> None:
        """Test init process with no args."""
        mock_env = mocker.patch(f"{MODULE}.DeployEnvironment")
        mock_inject = mocker.patch.object(
            Context, "_Context__inject_profile_credentials"
        )

        obj = Context()
        assert obj.command is None
        mock_env.assert_called_once_with()
        mock_inject.assert_called_once_with()
