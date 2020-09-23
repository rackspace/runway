"""Replicated Lambda Function cleanup warning."""
import logging
from typing import Any, Dict, List  # pylint: disable=unused-import

from runway.cfngin.context import Context  # pylint: disable=unused-import
from runway.cfngin.providers.base import BaseProvider  # pylint: disable=W

LOGGER = logging.getLogger(__name__)
STACK_STATUSES_TO_IGNORE = [
    "ROLLBACK_IN_PROGRESS",
    "ROLLBACK_FAILED",
    "ROLLBACK_COMPLETE",
    "DELETE_IN_PROGRESS",
    "DELETE_FAILED",
    "DELETE_COMPLETE",
    "IMPORT_ROLLBACK_IN_PROGRESS",
    "IMPORT_ROLLBACK_FAILED",
    "IMPORT_ROLLBACK_COMPLETE",
]


def get_replicated_function_names(
    outputs,  # type: List[Dict[str, str]]
):
    # type: (...) -> List[str]
    """Extract replicated function names from CFN outputs."""
    function_names = []
    for i in [
        "LambdaCheckAuthArn",
        "LambdaHttpHeadersArn",
        "LambdaParseAuthArn",
        "LambdaRefreshAuthArn",
        "LambdaSignOutArn",
        "LambdaCFDirectoryIndexRewriteArn",
    ]:
        function_arn = next(
            (
                output.get("OutputValue")
                for output in outputs
                if output.get("OutputKey") == i
            ),
            None,
        )
        if function_arn:
            function_names.append(function_arn.split(":")[-1])
    return function_names


def warn(
    context,  # type: Context # pylint: disable=unused-argument
    provider,  # type: BaseProvider # pylint: disable=unused-argument
    **kwargs  # type: Dict[str, Any]
):
    # type: (...) -> bool
    """Notify the user of Lambda functions to delete.

    Args:
        context (:class:`runway.cfngin.context.Context`): The context
            instance.
        provider (:class:`runway.cfngin.providers.base.BaseProvider`):
            The provider instance.

    Keyword Args:
        stack_relative_name (str): CFNgin stack name with Functions.

    """
    site_stack_name = (
        context.namespace + context.namespace_delimiter + kwargs["stack_relative_name"]
    )
    session = context.get_session()
    cfn_client = session.client("cloudformation")
    try:
        describe_response = cfn_client.describe_stacks(StackName=site_stack_name)
        stack = next(
            x
            for x in describe_response.get("Stacks", [])
            if (
                x.get("StackStatus")
                and x.get("StackStatus") not in STACK_STATUSES_TO_IGNORE
            )
        )
        functions = get_replicated_function_names(stack["Outputs"])
        if functions:
            runway_cmd = (
                "runway run-aws -- lambda delete-function "
                "--function-name $x --region %s" % context.region
            )
            LOGGER.warning(
                "About to delete the Static Site stack that contains "
                "replicated Lambda functions. These functions cannot "
                "be deleted until AWS automatically deletes their "
                "replicas. After some time has passed (a day is "
                "typically sufficient), they can be manually deleted. "
                "E.g.:"
            )
            LOGGER.warning("On macOS/Linux:")
            LOGGER.warning(
                "for x in %s; do %s; done", (" ").join(functions), runway_cmd
            )
            LOGGER.warning("On Windows:")
            LOGGER.warning(
                'Foreach ($x in "%s") { %s }', ('","').join(functions), runway_cmd
            )
    except Exception:  # pylint: disable=broad-except
        # There's no harm in continuing on in the event of an error
        # Orphanized functions have no cost
        pass
    return True
