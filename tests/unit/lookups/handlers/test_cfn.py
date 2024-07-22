"""Test runway.lookups.handlers.cfn."""

# pyright: basic, reportFunctionMemberAccess=none
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
from unittest.mock import MagicMock

import boto3
import pytest
from botocore.exceptions import ClientError
from botocore.stub import Stubber

from runway.cfngin.exceptions import StackDoesNotExist
from runway.cfngin.providers.aws.default import Provider
from runway.exceptions import OutputDoesNotExist
from runway.lookups.handlers.cfn import CfnLookup, OutputQuery

if TYPE_CHECKING:
    from mypy_boto3_cloudformation.client import CloudFormationClient
    from pytest_mock import MockerFixture

    from ...factories import MockRunwayContext


def generate_describe_stacks_stack(
    stack_name: str,
    outputs: dict[str, str],
    creation_time: Optional[datetime] = None,
    stack_status: str = "CREATE_COMPLETE",
) -> dict[str, Any]:
    """Generate describe stacks stack.

    Args:
        stack_name: Name of the stack.
        outputs: Dictionary to be converted to stack outputs.
        creation_time (Optional[datetime.datetime]): Stack creation time.
        stack_status: Current stack status.

    Returns:
        Mock describe stacks['Stacks'] list item.

    """
    return {
        "StackName": stack_name,
        "StackId": stack_name,
        "CreationTime": creation_time or datetime(2015, 1, 1),
        "StackStatus": stack_status,
        "Tags": [],
        "EnableTerminationProtection": False,
        "Outputs": [
            {"OutputKey": k, "OutputValue": v, "Description": "test output"}
            for k, v in outputs.items()
        ],
    }


def setup_cfn_client() -> tuple[CloudFormationClient, Stubber]:
    """Create a CloudFormation client & Stubber."""
    client = boto3.client("cloudformation")
    return client, Stubber(client)


class TestCfnLookup:
    """Test runway.lookups.handlers.cfn.CfnLookup."""

    def test_handle(self, mocker: MockerFixture) -> None:
        """Test handle."""
        mock_format_results = mocker.patch.object(
            CfnLookup, "format_results", return_value="success"
        )
        mock_get_stack_output = mocker.patch.object(
            CfnLookup, "get_stack_output", return_value="cls.success"
        )
        mock_should_use = mocker.patch.object(
            CfnLookup, "should_use_provider", side_effect=[True, False]
        )
        mock_context = MagicMock(name="context")
        mock_session = MagicMock(name="session")
        mock_context.get_session.return_value = mock_session
        mock_session.client.return_value = mock_session
        mock_provider = MagicMock(name="provider")
        mock_provider.get_output.return_value = "provider.success"

        raw_query = "test-stack.output1"
        query = OutputQuery(*raw_query.split("."))
        region = "us-west-2"
        args = f"::region={region}"
        value = raw_query + args
        mock_parse = mocker.patch.object(
            CfnLookup, "parse", return_value=(raw_query, {"region": region})
        )

        # test happy path when used from CFNgin (provider)
        assert CfnLookup.handle(value, context=mock_context, provider=mock_provider) == "success"
        mock_parse.assert_called_once_with(value)
        mock_provider.get_output.assert_called_once_with(*query)
        mock_should_use.assert_called_once_with({"region": region}, mock_provider)
        mock_format_results.assert_called_once_with("provider.success", region=region)
        mock_context.get_session.assert_not_called()
        mock_get_stack_output.assert_not_called()

        # test happy path when use from runway (no provider)
        assert CfnLookup.handle(value, context=mock_context) == "success"
        mock_should_use.assert_called_with({"region": region}, None)
        mock_context.get_session.assert_called_once_with(region=region)
        mock_session.client.assert_called_once_with("cloudformation")
        mock_get_stack_output.assert_called_once_with(mock_session, query)
        mock_format_results.assert_called_with("cls.success", region=region)

    @pytest.mark.parametrize(
        "exception, default",
        [
            (ClientError({"Error": {"Code": "", "Message": ""}}, "something"), None),
            (
                ClientError({"Error": {"Code": "", "Message": ""}}, "something"),
                "something",
            ),
            (KeyError, None),
            (KeyError, "something"),
        ],
    )
    def test_handle_exception(
        self,
        caplog: pytest.LogCaptureFixture,
        default: Optional[str],
        exception: Exception,
        mocker: MockerFixture,
    ) -> None:
        """Test handle cls.get_stack_output raise exception."""
        caplog.set_level(logging.DEBUG, logger="runway.lookups.handlers.cfn")
        mock_should_use = mocker.patch.object(CfnLookup, "should_use_provider", return_value=False)
        mock_context = MagicMock(name="context")
        mock_session = MagicMock(name="session")
        mock_context.get_session.return_value = mock_session
        mock_session.client.return_value = mock_session
        mocker.patch.object(CfnLookup, "get_stack_output", MagicMock())
        CfnLookup.get_stack_output.side_effect = exception

        raw_query = "test-stack.output1"
        query = OutputQuery(*raw_query.split("."))

        if default:
            assert CfnLookup.handle(raw_query + "::default=" + default, mock_context) == default
            mock_should_use.assert_called_once_with({"default": default}, None)
            assert (
                "unable to resolve lookup for CloudFormation Stack output "
                f'"{raw_query}"; using default'
            ) in caplog.messages
        else:
            if isinstance(exception, (ClientError, StackDoesNotExist)):
                with pytest.raises(type(exception)):
                    assert not CfnLookup.handle(raw_query, mock_context)
            else:
                with pytest.raises(OutputDoesNotExist) as excinfo:
                    assert not CfnLookup.handle(raw_query, mock_context)
                assert excinfo.value.stack_name == "test-stack"
                assert excinfo.value.output == "output1"
            mock_should_use.assert_called_once_with({}, None)

        mock_context.get_session.assert_called_once()
        mock_session.client.assert_called_once_with("cloudformation")
        CfnLookup.get_stack_output.assert_called_once_with(mock_session, query)

    @pytest.mark.parametrize(
        "exception, default",
        [
            (ClientError({"Error": {"Code": "", "Message": ""}}, "something"), None),
            (
                ClientError({"Error": {"Code": "", "Message": ""}}, "something"),
                "something",
            ),
            (KeyError, None),
            (KeyError, "something"),
            (StackDoesNotExist("test-stack", "output1"), None),
            (StackDoesNotExist("test-stack", "output1"), "something"),
        ],
    )
    def test_handle_provider_exception(
        self,
        caplog: pytest.LogCaptureFixture,
        default: Optional[str],
        exception: Exception,
        mocker: MockerFixture,
        runway_context: MockRunwayContext,
    ) -> None:
        """Test handle provider raise exception."""
        caplog.set_level(logging.DEBUG, logger="runway.lookups.handlers.cfn")
        mock_should_use = mocker.patch.object(CfnLookup, "should_use_provider", return_value=True)
        mock_provider = MagicMock(region="us-east-1")
        mock_provider.get_output.side_effect = exception
        raw_query = "test-stack.output1"

        if default:
            assert (
                CfnLookup.handle(
                    raw_query + "::default=" + default,
                    context=runway_context,
                    provider=mock_provider,
                )
                == default
            )
            mock_should_use.assert_called_once_with({"default": default}, mock_provider)
            assert (
                "unable to resolve lookup for CloudFormation Stack output "
                f'"{raw_query}"; using default'
            ) in caplog.messages
        else:
            if isinstance(exception, (ClientError, StackDoesNotExist)):
                with pytest.raises(type(exception)):
                    assert not CfnLookup.handle(
                        raw_query, context=runway_context, provider=mock_provider
                    )
            else:
                with pytest.raises(OutputDoesNotExist) as excinfo:
                    assert not CfnLookup.handle(
                        raw_query, context=runway_context, provider=mock_provider
                    )
                assert excinfo.value.stack_name == "test-stack"
                assert excinfo.value.output == "output1"
            mock_should_use.assert_called_once_with({}, mock_provider)
        mock_provider.get_output.assert_called_once_with("test-stack", "output1")

    def test_handle_valueerror(self, runway_context: MockRunwayContext) -> None:
        """Test handle raising ValueError."""
        with pytest.raises(ValueError, match="query must be <stack-name>.<output-name>"):
            assert CfnLookup.handle("something", runway_context)

    def test_get_stack_output(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test get_stack_output."""
        caplog.set_level(logging.DEBUG, logger="runway.lookups.handlers.cfn")
        client, stubber = setup_cfn_client()
        stack_name = "test-stack"
        outputs = {"output1": "val1", "output2": "val2"}
        query = OutputQuery(stack_name, "output1")

        stubber.add_response(
            "describe_stacks",
            {"Stacks": [generate_describe_stacks_stack(stack_name, outputs)]},
            {"StackName": stack_name},
        )

        with stubber:
            assert CfnLookup.get_stack_output(client, query) == "val1"

        stubber.assert_no_pending_responses()
        assert f"describing stack: {stack_name}" in caplog.messages
        assert f"{stack_name} stack outputs: {json.dumps(outputs)}" in caplog.messages

    def test_get_stack_output_clienterror(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test get_stack_output raising ClientError."""
        caplog.set_level(logging.DEBUG, logger="runway.lookups.handlers.cfn")
        client, stubber = setup_cfn_client()
        stack_name = "test-stack"
        query = OutputQuery(stack_name, "output1")

        stubber.add_client_error(
            "describe_stacks",
            service_error_code="ValidationError",
            service_message=f"Stack {stack_name} does not exist",
            expected_params={"StackName": stack_name},
        )

        with stubber, pytest.raises(ClientError):
            assert CfnLookup.get_stack_output(client, query)

        stubber.assert_no_pending_responses()
        assert f"describing stack: {stack_name}" in caplog.messages

    def test_get_stack_output_keyerror(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test get_stack_output raising KeyError."""
        caplog.set_level(logging.DEBUG, logger="runway.lookups.handlers.cfn")
        client, stubber = setup_cfn_client()
        stack_name = "test-stack"
        outputs = {"output2": "val2"}
        query = OutputQuery(stack_name, "output1")

        stubber.add_response(
            "describe_stacks",
            {"Stacks": [generate_describe_stacks_stack(stack_name, outputs)]},
            {"StackName": stack_name},
        )

        with stubber, pytest.raises(KeyError):
            assert CfnLookup.get_stack_output(client, query)

        stubber.assert_no_pending_responses()
        assert f"describing stack: {stack_name}" in caplog.messages
        assert f"{stack_name} stack outputs: {json.dumps(outputs)}" in caplog.messages

    @pytest.mark.parametrize(
        "args, provider",
        [
            ({}, None),
            ({"region": "us-west-2"}, MagicMock(autospec=Provider, region="us-east-1")),
        ],
    )
    def test_should_use_provider_falsy(
        self,
        args: dict[str, Any],
        caplog: pytest.LogCaptureFixture,
        provider: Optional[Provider],
    ) -> None:
        """Test should_use_provider with falsy cases."""
        caplog.set_level(logging.DEBUG, logger="runway.lookups.handlers.cfn")
        assert not CfnLookup.should_use_provider(args, provider)
        if provider:
            assert "not using provider; requested region does not match" in caplog.messages
            assert "using provider" not in caplog.messages

    @pytest.mark.parametrize(
        "args, provider",
        [
            ({}, MagicMock(autospec=Provider)),
            ({"region": "us-east-1"}, MagicMock(autospec=Provider, region="us-east-1")),
        ],
    )
    def test_should_use_provider_truthy(
        self,
        args: dict[str, Any],
        caplog: pytest.LogCaptureFixture,
        provider: Optional[Provider],
    ) -> None:
        """Test should_use_provider with truthy cases."""
        caplog.set_level(logging.DEBUG, logger="runway.lookups.handlers.cfn")
        assert CfnLookup.should_use_provider(args, provider)
        assert "using provider" in caplog.messages


def test_outputquery() -> None:
    """Test OutputQuery."""
    result = OutputQuery("stack_name", "output_name")
    assert result.stack_name == "stack_name"
    assert result.output_name == "output_name"
