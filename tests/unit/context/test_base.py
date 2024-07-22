"""Test runway.context._base."""

# pyright: basic
from __future__ import annotations

from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock

import boto3
import pytest

from runway.context._base import BaseContext
from runway.context.sys_info import SystemInfo
from runway.core.components import DeployEnvironment

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

MODULE = "runway.context._base"

TEST_BOTO3_CREDS = {
    "aws_access_key_id": "foo",
    "aws_secret_access_key": "bar",
    "aws_session_token": "foobar",
}
TEST_ENV_CREDS = {
    "AWS_ACCESS_KEY_ID": "foo",
    "AWS_SECRET_ACCESS_KEY": "bar",
    "AWS_SESSION_TOKEN": "foobar",
}


@pytest.fixture()
def mock_boto3_session(mocker: MockerFixture) -> MagicMock:
    """Mock boto3.Session."""
    mock_session = MagicMock(autospec=boto3.Session)
    mocker.patch(f"{MODULE}.boto3", Session=mock_session)
    return mock_session


@pytest.fixture()
def mock_sso_botocore_session(mocker: MockerFixture) -> MagicMock:
    """Mock runway.aws_sso_botocore.session.Session."""
    return mocker.patch(f"{MODULE}.Session")


class TestBaseContext:
    """Test runway.context._base.BaseContext."""

    env = DeployEnvironment(
        environ={
            "AWS_ACCESS_KEY_ID": "testing",
            "AWS_SECRET_ACCESS_KEY": "testing",
            "AWS_SESSION_TOKEN": "foobar",
            "AWS_DEFAULT_REGION": "us-east-1",
            "AWS_REGION": "us-east-1",
        },
        explicit_name="test",
    )

    def test_boto3_credentials(self, mocker: MockerFixture) -> None:
        """Test boto3_credentials."""
        mocker.patch.object(self.env, "vars", TEST_ENV_CREDS)
        assert BaseContext(deploy_environment=self.env).boto3_credentials == TEST_BOTO3_CREDS

    def test_boto3_credentials_empty(self, mocker: MockerFixture) -> None:
        """Test boto3_credentials empty."""
        mocker.patch.object(self.env, "vars", TEST_BOTO3_CREDS)
        assert not BaseContext(deploy_environment=self.env).boto3_credentials

    def test_current_aws_creds(self, mocker: MockerFixture) -> None:
        """Test current_aws_creds."""
        mocker.patch.object(self.env, "vars", TEST_ENV_CREDS)
        assert BaseContext(deploy_environment=self.env).current_aws_creds == TEST_ENV_CREDS

    def test_current_aws_creds_empty(self, mocker: MockerFixture) -> None:
        """Test current_aws_creds empty."""
        mocker.patch.object(self.env, "vars", TEST_BOTO3_CREDS)
        assert BaseContext(deploy_environment=self.env).current_aws_creds == {}

    def test_is_interactive(self, mocker: MockerFixture) -> None:
        """Test is_interactive."""
        mocker.patch.object(self.env, "ci", False)
        ctx = BaseContext(deploy_environment=self.env)
        assert ctx.is_interactive

        mocker.patch.object(self.env, "ci", True)
        assert not ctx.is_interactive

    def test_is_noninteractive(self, mocker: MockerFixture) -> None:
        """Test is_noninteractive."""
        mocker.patch.object(self.env, "ci", False)
        ctx = BaseContext(deploy_environment=self.env)
        assert not ctx.is_noninteractive

        mocker.patch.object(self.env, "ci", True)
        assert ctx.is_noninteractive

    def test_get_session(
        self, mock_boto3_session: MagicMock, mock_sso_botocore_session: MagicMock
    ) -> None:
        """Test get_session."""
        ctx = BaseContext(deploy_environment=self.env)
        assert ctx.get_session() == mock_boto3_session.return_value
        mock_boto3_session.assert_called_once_with(
            aws_access_key_id=self.env.vars["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=self.env.vars["AWS_SECRET_ACCESS_KEY"],
            aws_session_token=self.env.vars["AWS_SESSION_TOKEN"],
            botocore_session=mock_sso_botocore_session.return_value,
            region_name=self.env.aws_region,
            profile_name=None,
        )
        mock_boto3_session.return_value._session.get_component.assert_called_once_with(
            "credential_provider"
        )
        cred_provider = cast(
            MagicMock,
            mock_boto3_session.return_value._session.get_component.return_value,
        )
        cred_provider.get_provider.assert_called_once_with("assume-role")
        provider = cast(MagicMock, cred_provider.get_provider.return_value)
        assert provider.cache == {}

    def test_get_session_with_creds(
        self, mock_boto3_session: MagicMock, mock_sso_botocore_session: MagicMock
    ) -> None:
        """Test get_session with credentials."""
        ctx = BaseContext(deploy_environment=self.env)
        assert ctx.get_session(**TEST_BOTO3_CREDS) == mock_boto3_session.return_value
        mock_boto3_session.assert_called_once_with(
            aws_access_key_id=TEST_BOTO3_CREDS["aws_access_key_id"],
            aws_secret_access_key=TEST_BOTO3_CREDS["aws_secret_access_key"],
            aws_session_token=TEST_BOTO3_CREDS["aws_session_token"],
            botocore_session=mock_sso_botocore_session.return_value,
            region_name=self.env.aws_region,
            profile_name=None,
        )

    def test_get_session_with_profile(
        self, mock_boto3_session: MagicMock, mock_sso_botocore_session: MagicMock
    ) -> None:
        """Test get_session with profile."""
        ctx = BaseContext(deploy_environment=self.env)
        assert ctx.get_session(profile="something") == mock_boto3_session.return_value
        mock_boto3_session.assert_called_once_with(
            aws_access_key_id=None,
            aws_secret_access_key=None,
            aws_session_token=None,
            botocore_session=mock_sso_botocore_session.return_value,
            region_name=self.env.aws_region,
            profile_name="something",
        )

    def test_get_session_with_region(
        self, mock_boto3_session: MagicMock, mock_sso_botocore_session: MagicMock
    ) -> None:
        """Test get_session with region."""
        ctx = BaseContext(deploy_environment=self.env)
        assert ctx.get_session(region="us-east-2") == mock_boto3_session.return_value
        mock_boto3_session.assert_called_once_with(
            aws_access_key_id=self.env.vars["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=self.env.vars["AWS_SECRET_ACCESS_KEY"],
            aws_session_token=self.env.vars["AWS_SESSION_TOKEN"],
            botocore_session=mock_sso_botocore_session.return_value,
            region_name="us-east-2",
            profile_name=None,
        )

    def test_sys_info(self) -> None:
        """Test sys_info."""
        assert isinstance(BaseContext(deploy_environment=self.env).sys_info, SystemInfo)
