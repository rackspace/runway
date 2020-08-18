"""Test runway.core.providers.aws._assume_role."""
# pylint: disable=no-self-use
import logging
from datetime import datetime

from runway.core.providers.aws import AssumeRole

NEW_CREDENTIALS = {
    "AWS_ACCESS_KEY_ID": "new_access_key_id",
    "AWS_SECRET_ACCESS_KEY": "new_secret_access_key",
    "AWS_SESSION_TOKEN": "new_session_token",
}
ROLE_ARN = "arn:aws:iam::123456789012:role/role-name"
ROLE_SESSION_ARN = "arn:aws:sts::123456789012:assumed-role/role-name/"


def test_assume_role(runway_context):
    """Test AssumeRole."""
    assumed_role_user = {
        "AssumedRoleId": NEW_CREDENTIALS["AWS_ACCESS_KEY_ID"] + ":runway",
        "Arn": ROLE_SESSION_ARN + "runway",
    }
    credentials = {
        "AccessKeyId": NEW_CREDENTIALS["AWS_ACCESS_KEY_ID"],
        "SecretAccessKey": NEW_CREDENTIALS["AWS_SECRET_ACCESS_KEY"],
        "SessionToken": NEW_CREDENTIALS["AWS_SESSION_TOKEN"],
        "Expiration": datetime(2015, 1, 1),
    }
    stubber = runway_context.add_stubber("sts")
    stubber.add_response(
        "assume_role",
        {"Credentials": credentials, "AssumedRoleUser": assumed_role_user},
        {"RoleArn": ROLE_ARN, "RoleSessionName": "runway", "DurationSeconds": 3600},
    )

    assert runway_context.env.aws_credentials != NEW_CREDENTIALS

    with stubber, AssumeRole(runway_context, role_arn=ROLE_ARN) as result:
        assert runway_context.env.aws_credentials == NEW_CREDENTIALS
        assert result.role_arn == ROLE_ARN
        assert result.duration_seconds == 3600
        assert result.revert_on_exit is True
        assert result.session_name == "runway"
        assert result.assumed_role_user == assumed_role_user
        assert result.credentials == credentials
        for key in NEW_CREDENTIALS:  # these should exist from pytest autouse fixture
            assert "OLD_" + key in runway_context.env.vars
    assert runway_context.env.aws_credentials != NEW_CREDENTIALS
    for key in NEW_CREDENTIALS:
        assert "OLD_" + key not in runway_context.env.vars


def test_assume_role_no_revert_on_exit(runway_context):
    """Test AssumeRole revert on exit."""
    assumed_role_user = {
        "AssumedRoleId": NEW_CREDENTIALS["AWS_ACCESS_KEY_ID"] + ":runway-test",
        "Arn": ROLE_SESSION_ARN + "runway-test",
    }
    credentials = {
        "AccessKeyId": NEW_CREDENTIALS["AWS_ACCESS_KEY_ID"],
        "SecretAccessKey": NEW_CREDENTIALS["AWS_SECRET_ACCESS_KEY"],
        "SessionToken": NEW_CREDENTIALS["AWS_SESSION_TOKEN"],
        "Expiration": datetime(2015, 1, 1),
    }
    stubber = runway_context.add_stubber("sts")
    stubber.add_response(
        "assume_role",
        {"Credentials": credentials, "AssumedRoleUser": assumed_role_user},
        {"RoleArn": ROLE_ARN, "RoleSessionName": "runway-test", "DurationSeconds": 900},
    )

    assert runway_context.env.aws_credentials != NEW_CREDENTIALS

    with stubber, AssumeRole(
        runway_context,
        role_arn=ROLE_ARN,
        duration_seconds=900,
        revert_on_exit=False,
        session_name="runway-test",
    ) as result:
        assert runway_context.env.aws_credentials == NEW_CREDENTIALS
        assert result.role_arn == ROLE_ARN
        assert result.duration_seconds == 900
        assert result.revert_on_exit is False
        assert result.session_name == "runway-test"
        assert result.assumed_role_user == assumed_role_user
        assert result.credentials == credentials
    assert runway_context.env.aws_credentials == NEW_CREDENTIALS


def test_assume_role_no_role(caplog, runway_context):
    """Test AssumeRole with no role_arn."""
    caplog.set_level(logging.DEBUG, logger="runway")
    with AssumeRole(runway_context) as result:
        assert not result.assumed_role_user
        assert not result.credentials
        assert not result.role_arn
    assert "no role to assume" in caplog.messages
