"""Test runway.cfngin.hooks.staticsite.cleanup."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import pytest

from runway._logging import LogLevels
from runway.cfngin.hooks.staticsite.cleanup import (
    REPLICATED_FUNCTION_OUTPUTS,
    get_replicated_function_names,
    warn,
)

if TYPE_CHECKING:
    from mypy_boto3_cloudformation.type_defs import OutputTypeDef
    from pytest import LogCaptureFixture
    from pytest_mock import MockerFixture

    from ....factories import MockCFNginContext

MODULE = "runway.cfngin.hooks.staticsite.cleanup"


@pytest.mark.parametrize(
    "outputs, expected",
    [
        ([], []),
        (
            [
                {"OutputKey": i, "OutputValue": f"{i}Val"}
                for i in REPLICATED_FUNCTION_OUTPUTS
            ]
            + [{"OutputKey": "foo", "OutputValue": "bar"}],
            [f"{i}Val" for i in REPLICATED_FUNCTION_OUTPUTS],
        ),
    ],
)
def test_get_replicated_function_names(
    expected: list[str], outputs: list[OutputTypeDef]
) -> None:
    """Test get_replicated_function_names."""
    assert get_replicated_function_names(outputs) == expected


def test_warn(
    caplog: LogCaptureFixture, cfngin_context: MockCFNginContext, mocker: MockerFixture
) -> None:
    """Test warn."""
    caplog.set_level(LogLevels.WARNING, MODULE)
    outputs = [{"OutputKey": "foo", "OutputValue": "bar"}]
    mock_get_func_names = mocker.patch(
        f"{MODULE}.get_replicated_function_names", return_value=["foo", "foobar"]
    )
    stubber = cfngin_context.add_stubber("cloudformation")

    stubber.add_response(
        "describe_stacks",
        {
            "Stacks": [
                {
                    "CreationTime": datetime(2015, 1, 1),
                    "Outputs": outputs,
                    "StackName": f"{cfngin_context.namespace}-stack-name",
                    "StackStatus": "CREATE_COMPLETE",
                }
            ]
        },
        {"StackName": f"{cfngin_context.namespace}-stack-name"},
    )

    with stubber:
        assert warn(cfngin_context, stack_relative_name="stack-name")
    stubber.assert_no_pending_responses()
    mock_get_func_names.assert_called_once_with(outputs)

    logs = "\n".join(caplog.messages)
    assert "for x in foo foobar;" in logs


def test_warn_ignore_client_error(
    caplog: LogCaptureFixture, cfngin_context: MockCFNginContext
) -> None:
    """Test warn ignore ClientError."""
    caplog.set_level(LogLevels.WARNING, MODULE)
    stubber = cfngin_context.add_stubber("cloudformation")

    stubber.add_client_error("describe_stacks")

    with stubber:
        assert warn(cfngin_context, stack_relative_name="stack-name")
    stubber.assert_no_pending_responses()
    assert not caplog.messages
