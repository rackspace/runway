"""Retrieve a value from CloudFormation Stack Outputs.

The query syntax for this lookup is ``<stack-name>.<output-name>``.
When specifying the output name, be sure to use the *Logical ID* of
the output; not the *Export.Name*.

"""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, Dict, NamedTuple, Optional, Union, cast

from botocore.exceptions import ClientError

from ...cfngin.exceptions import StackDoesNotExist
from ...exceptions import OutputDoesNotExist
from .base import LookupHandler

if TYPE_CHECKING:
    from mypy_boto3_cloudformation.client import CloudFormationClient

    from ...cfngin.providers.aws.default import Provider
    from ...context import CfnginContext, RunwayContext

LOGGER = logging.getLogger(__name__)
TYPE_NAME = "cfn"


class OutputQuery(NamedTuple):
    """Output query NamedTuple."""

    stack_name: str
    output_name: str


class CfnLookup(LookupHandler):
    """CloudFormation Stack Output lookup."""

    @staticmethod
    def should_use_provider(args: Dict[str, str], provider: Optional[Provider]) -> bool:
        """Determine if the provider should be used for the lookup.

        This will open happen when the lookup is used with CFNgin.

        Args:
            args: Parsed arguments provided to the lookup.
            provider: CFNgin provider.

        """
        if provider:
            if args.get("region") and provider.region != args["region"]:
                LOGGER.debug("not using provider; requested region does not match")
                return False
            LOGGER.debug("using provider")
            return True
        return False

    @staticmethod
    def get_stack_output(client: CloudFormationClient, query: OutputQuery) -> str:
        """Get CloudFormation Stack output.

        Args:
            client: Boto3 CloudFormation client.
            query: What to get.

        """
        LOGGER.debug("describing stack: %s", query.stack_name)
        stack = client.describe_stacks(StackName=query.stack_name)["Stacks"][0]
        outputs = {
            # these should always exist even though the schema says they are not required
            output["OutputKey"]: output["OutputValue"]  # type: ignore
            for output in stack.get("Outputs", [])
        }
        LOGGER.debug("%s stack outputs: %s", stack["StackName"], json.dumps(outputs))
        return outputs[query.output_name]

    @classmethod
    def handle(  # pylint: disable=arguments-differ
        cls,
        value: str,
        context: Union[CfnginContext, RunwayContext],
        *,
        provider: Optional[Provider] = None,
        **_: Any,
    ) -> Any:
        """Retrieve a value from CloudFormation Stack outputs.

        Args:
            value: The value passed to the Lookup.
            context: The current context object.
            provider: AWS provider.

        Returns:
            Result of the query.

        Raises:
            OutputDoesNotExist: Output does not exist on the Stack provided
                and default was not provided.

        """
        raw_query, args = cls.parse(value)
        try:
            query = OutputQuery(*raw_query.split("."))
        except TypeError as exc:
            raise ValueError(
                f'query must be <stack-name>.<output-name>; got "{raw_query}"'
            ) from exc

        try:
            # dict is not perserved in mock call so it must be a copy of
            # args for testing to function correctly
            if cls.should_use_provider(args.copy(), provider):
                # this will only happen when used from cfngin
                result = cast("Provider", provider).get_output(
                    query.stack_name, query.output_name
                )
            else:
                cfn_client = context.get_session(region=args.get("region")).client(
                    "cloudformation"
                )
                result = cls.get_stack_output(cfn_client, query)
        except (ClientError, KeyError, StackDoesNotExist) as exc:
            # StackDoesNotExist is only raised by provider
            if "default" in args:
                LOGGER.debug(
                    "unable to resolve lookup for CloudFormation Stack "
                    'output "%s"; using default',
                    raw_query,
                    exc_info=True,
                )
                args.pop("load", None)  # don't load a default value
                result = args.pop("default")
            elif isinstance(exc, (ClientError, StackDoesNotExist)):
                raise
            else:
                raise OutputDoesNotExist(query.stack_name, query.output_name) from exc
        return cls.format_results(result, **args)
