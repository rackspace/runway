"""Test runway.lookups.handlers.cfn."""
# pylint: disable=no-self-use
import json
import logging
from datetime import datetime

import boto3
import pytest
from botocore.exceptions import ClientError
from botocore.stub import Stubber
from mock import MagicMock, patch

from runway.cfngin.exceptions import OutputDoesNotExist, StackDoesNotExist
from runway.lookups.handlers.cfn import TYPE_NAME, CfnLookup, OutputQuery


def generate_describe_stacks_stack(
    stack_name, outputs, creation_time=None, stack_status="CREATE_COMPLETE"
):
    """Generate describe stacks stack.

    Args:
        stack_name (str): Name of the stack.
        outputs (Dict[str, str]): Dictionary to be converted to stack outputs.
        creation_time (Optional[datetime.datetime]): Stack creation time.
        stack_status (str): Current stack status.

    Returns:
        Dict[str, Any]: Mock describe stacks['Stacks'] list item.

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


def setup_cfn_client():
    """Create a CloudFormation client & Stubber.

    Returns:
        client, Stubber: CloudFormation client and Stubber.

    """
    client = boto3.client("cloudformation")
    return client, Stubber(client)


class TestCfnLookup(object):
    """Test runway.lookups.handlers.cfn.CfnLookup."""

    @patch.object(CfnLookup, "format_results")
    @patch.object(CfnLookup, "parse")
    @patch.object(CfnLookup, "get_stack_output")
    @patch.object(CfnLookup, "should_use_provider")
    def test_handle(
        self, mock_should_use, mock_get_stack_output, mock_parse, mock_format_results
    ):
        """Test handle."""
        mock_should_use.side_effect = [True, False]
        mock_format_results.return_value = "success"
        mock_context = MagicMock(name="context")
        mock_get_stack_output.return_value = "cls.success"
        mock_session = MagicMock(name="session")
        mock_context.get_session.return_value = mock_session
        mock_session.client.return_value = mock_session
        mock_provider = MagicMock(name="provider")
        mock_provider.get_output.return_value = "provider.success"

        raw_query = "test-stack.output1"
        query = OutputQuery(*raw_query.split("."))
        region = "us-west-2"
        args = "::region={region}".format(region=region)
        value = raw_query + args
        mock_parse.return_value = (raw_query, {"region": region})

        # test happy path when used from CFNgin (provider)
        assert (
            CfnLookup.handle(value, context=mock_context, provider=mock_provider)
            == "success"
        )
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
            (ClientError({}, "something"), None),
            (ClientError({}, "something"), "something"),
            (KeyError, None),
            (KeyError, "something"),
        ],
    )
    @patch.object(CfnLookup, "should_use_provider")
    def test_handle_exception(
        self, mock_should_use, exception, default, caplog, monkeypatch
    ):
        """Test handle cls.get_stack_output raise exception."""
        caplog.set_level(logging.DEBUG, logger="runway.lookups.handlers.cfn")
        mock_context = MagicMock(name="context")
        mock_session = MagicMock(name="session")
        mock_context.get_session.return_value = mock_session
        mock_session.client.return_value = mock_session
        mock_should_use.return_value = False
        monkeypatch.setattr(CfnLookup, "get_stack_output", MagicMock())
        CfnLookup.get_stack_output.side_effect = exception

        raw_query = "test-stack.output1"
        query = OutputQuery(*raw_query.split("."))

        if default:
            assert (
                CfnLookup.handle(raw_query + "::default=" + default, mock_context)
                == default
            )
            mock_should_use.assert_called_once_with({"default": default}, None)
            assert (
                "unable to resolve lookup for CloudFormation Stack output "
                '"{}"; using default'.format(raw_query)
            ) in caplog.messages
        else:
            if isinstance(exception, (ClientError, StackDoesNotExist)):
                with pytest.raises(exception.__class__):
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
            (ClientError({}, "something"), None),
            (ClientError({}, "something"), "something"),
            (KeyError, None),
            (KeyError, "something"),
            (StackDoesNotExist("test-stack", "output1"), None),
            (StackDoesNotExist("test-stack", "output1"), "something"),
        ],
    )
    @patch.object(CfnLookup, "should_use_provider")
    def test_handle_provider_exception(
        self, mock_should_use, exception, default, caplog
    ):
        """Test handle provider raise exception."""
        caplog.set_level(logging.DEBUG, logger="runway.lookups.handlers.cfn")
        mock_should_use.return_value = True
        mock_provider = MagicMock(region="us-east-1")
        mock_provider.get_output.side_effect = exception
        raw_query = "test-stack.output1"

        if default:
            assert (
                CfnLookup.handle(
                    raw_query + "::default=" + default,
                    context=None,
                    provider=mock_provider,
                )
                == default
            )
            mock_should_use.assert_called_once_with({"default": default}, mock_provider)
            assert (
                "unable to resolve lookup for CloudFormation Stack output "
                '"{}"; using default'.format(raw_query)
            ) in caplog.messages
        else:
            if isinstance(exception, (ClientError, StackDoesNotExist)):
                with pytest.raises(exception.__class__):
                    assert not CfnLookup.handle(
                        raw_query, context=None, provider=mock_provider
                    )
            else:
                with pytest.raises(OutputDoesNotExist) as excinfo:
                    assert not CfnLookup.handle(
                        raw_query, context=None, provider=mock_provider
                    )
                assert excinfo.value.stack_name == "test-stack"
                assert excinfo.value.output == "output1"
            mock_should_use.assert_called_once_with({}, mock_provider)
        mock_provider.get_output.assert_called_once_with("test-stack", "output1")

    def test_handle_valueerror(self):
        """Test handle raising ValueError."""
        with pytest.raises(ValueError) as excinfo:
            assert CfnLookup.handle("something", None)
        assert (
            str(excinfo.value)
            == 'query must be <stack-name>.<output-name>; got "something"'
        )

    def test_get_stack_output(self, caplog):
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
        assert "describing stack: %s" % stack_name in caplog.messages
        assert (
            "{} stack outputs: {}".format(stack_name, json.dumps(outputs))
            in caplog.messages
        )

    def test_get_stack_output_clienterror(self, caplog):
        """Test get_stack_output raising ClientError."""
        caplog.set_level(logging.DEBUG, logger="runway.lookups.handlers.cfn")
        client, stubber = setup_cfn_client()
        stack_name = "test-stack"
        query = OutputQuery(stack_name, "output1")

        stubber.add_client_error(
            "describe_stacks",
            service_error_code="ValidationError",
            service_message="Stack %s does not exist" % stack_name,
            expected_params={"StackName": stack_name},
        )

        with stubber, pytest.raises(ClientError):
            assert CfnLookup.get_stack_output(client, query)

        stubber.assert_no_pending_responses()
        assert "describing stack: %s" % stack_name in caplog.messages

    def test_get_stack_output_keyerror(self, caplog):
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
        assert "describing stack: %s" % stack_name in caplog.messages
        assert (
            "{} stack outputs: {}".format(stack_name, json.dumps(outputs))
            in caplog.messages
        )

    @pytest.mark.parametrize(
        "args, provider",
        [({}, None), ({"region": "us-west-2"}, MagicMock(region="us-east-1"))],
    )
    def test_should_use_provider_falsy(self, args, provider, caplog):
        """Test should_use_provider with falsy cases."""
        caplog.set_level(logging.DEBUG, logger="runway.lookups.handlers.cfn")
        assert not CfnLookup.should_use_provider(args, provider)
        if provider:
            assert (
                "not using provider; requested region does not match" in caplog.messages
            )
            assert "using provider" not in caplog.messages

    @pytest.mark.parametrize(
        "args, provider",
        [({}, MagicMock()), ({"region": "us-east-1"}, MagicMock(region="us-east-1"))],
    )
    def test_should_use_provider_truthy(self, args, provider, caplog):
        """Test should_use_provider with truthy cases."""
        caplog.set_level(logging.DEBUG, logger="runway.lookups.handlers.cfn")
        assert CfnLookup.should_use_provider(args, provider)
        assert "using provider" in caplog.messages


def test_outputquery():
    """Test OutputQuery."""
    result = OutputQuery("stack_name", "output_name")
    assert result.stack_name == "stack_name"
    assert result.output_name == "output_name"


def test_type_name():
    """Test runway.lookups.handlers.cfn.TYPE_NAME."""
    assert TYPE_NAME == "cfn"
