"""AWS Lambda test hooks."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from runway.context import CfnginContext

LOGGER = logging.getLogger("runway.cfngin.hooks.custom.awslambda_test")


def invoke(
    context: CfnginContext,
    *,
    expected_status_code: int = 200,
    function_name: str,
    **_: Any,
) -> bool:
    """Invoke AWS Lambda Function and check the response."""
    LOGGER.info("invoking %s", function_name)
    assert (
        context.get_session()
        .client("lambda")
        .invoke(FunctionName=function_name, InvocationType="RequestResponse")
        .get("StatusCode")
        == expected_status_code
    )
    LOGGER.info("%s returned %s", function_name, expected_status_code)
    return True
