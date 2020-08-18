"""Tests for update_urls."""
# pylint: disable=no-member
from unittest.mock import ANY, MagicMock, call, patch

import boto3
import pytest
from botocore.stub import Stubber
from click.testing import CliRunner
from mypy_boto3_dynamodb.service_resource import Table

from update_urls import command, handler, put_item, sanitize_version


def test_sanitize_version():
    """Test sanitize_version."""
    assert sanitize_version(None, None, "1.0.0") == "1.0.0"
    assert sanitize_version(None, None, "v1.0.0") == "1.0.0"
    assert sanitize_version(None, None, "refs/tags/1.0.0") == "1.0.0"
    assert sanitize_version(None, None, "refs/tags/v1.0.0") == "1.0.0"
    assert sanitize_version(None, None, "refs/tags/v1.0.0-dev1") == "1.0.0-dev1"

    with pytest.raises(ValueError):
        assert not sanitize_version(None, None, "refs/tags/stable")


def test_put_item():
    """Test put_item."""
    table_name = "test-table"
    id_val = "my_id"
    target = "my_target"
    table: Table = boto3.resource("dynamodb").Table(table_name)
    stubber = Stubber(table.meta.client)

    stubber.add_response(
        "put_item", {"Attributes": {"id": {"S": id_val}, "target": {"S": target}}}
    )

    with stubber:
        assert not put_item(table, id_val, target)


@patch("update_urls.put_item")
def test_handler(mock_put_item):
    """Test handler."""
    table = MagicMock()
    calls = []
    assert not handler(table, "test-bucket", "us-west-2", "1.0.0", True)
    calls.append(
        call(
            table=table,
            id_val="runway/latest/linux",
            target="https://test-bucket.s3-us-west-2.amazonaws.com/"
            "runway/1.0.0/linux/runway",
        )
    )
    calls.append(
        call(
            table=table,
            id_val="runway/1.0.0/linux",
            target="https://test-bucket.s3-us-west-2.amazonaws.com/"
            "runway/1.0.0/linux/runway",
        )
    )
    calls.append(
        call(
            table=table,
            id_val="runway/latest/osx",
            target="https://test-bucket.s3-us-west-2.amazonaws.com/"
            "runway/1.0.0/osx/runway",
        )
    )
    calls.append(
        call(
            table=table,
            id_val="runway/1.0.0/osx",
            target="https://test-bucket.s3-us-west-2.amazonaws.com/"
            "runway/1.0.0/osx/runway",
        )
    )
    calls.append(
        call(
            table=table,
            id_val="runway/latest/windows",
            target="https://test-bucket.s3-us-west-2.amazonaws.com/"
            "runway/1.0.0/windows/runway.exe",
        )
    )
    calls.append(
        call(
            table=table,
            id_val="runway/1.0.0/windows",
            target="https://test-bucket.s3-us-west-2.amazonaws.com/"
            "runway/1.0.0/windows/runway.exe",
        )
    )

    assert not handler(table, "test-bucket", "us-east-1", "1.1.0", False)
    calls.append(
        call(
            table=table,
            id_val="runway/1.1.0/linux",
            target="https://test-bucket.s3-us-east-1.amazonaws.com/"
            "runway/1.1.0/linux/runway",
        )
    )
    calls.append(
        call(
            table=table,
            id_val="runway/1.1.0/osx",
            target="https://test-bucket.s3-us-east-1.amazonaws.com/"
            "runway/1.1.0/osx/runway",
        )
    )
    calls.append(
        call(
            table=table,
            id_val="runway/1.1.0/windows",
            target="https://test-bucket.s3-us-east-1.amazonaws.com/"
            "runway/1.1.0/windows/runway.exe",
        )
    )

    mock_put_item.assert_has_calls(calls)


@patch("update_urls.handler")
def test_command(mock_handler):
    """Test command."""
    runner = CliRunner()
    result = runner.invoke(
        command,
        args=[
            "--bucket-name",
            "test-bucket",
            "--bucket-region",
            "us-west-2",
            "--version",
            "refs/tags/1.0.0",
            "--table",
            "test-table",
            "--latest",
        ],
        env={
            "AWS_ACCESS_KEY_ID": "testing",
            "AWS_SECRET_ACCESS_KEY": "testing",
            "AWS_DEFAULT_REGION": "us-east-1",
        },
    )
    assert result.exit_code == 0
    mock_handler.assert_called_once_with(ANY, "test-bucket", "us-west-2", "1.0.0", True)
