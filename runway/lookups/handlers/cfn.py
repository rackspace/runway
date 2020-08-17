"""Retrieve a value from CloudFormation Stack Outputs.

The query syntax for this lookup is ``<stack-name>.<output-name>``.
When specifying the output name, be sure to use the *Logical ID* of
the output; not the *Export.Name*.

If the Lookup is unable to find a CloudFormation Stack Output matching the
provided query, the default value is returned or an exception is raised
to show why the value could be be resolved (e.g. Stack does not exist or
output does not exist on the Stack).

.. seealso::
    https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/outputs-section-structure.html


.. rubric:: Arguments

This Lookup supports all :ref:`Common Lookup Arguments`.


.. rubric:: Example
.. code-block:: yaml
  :caption: Runway config

  deployments:
    - modules:
        path: sampleapp.tf
        options:
          terraform_backend_config:
            bucket: ${cfn common-tf-state.TerraformStateBucketName::region=us-east-1}
            dynamodb_table: ${cfn common-tf-state.TerraformStateTableName::region=us-east-1}
            region: us-east-1

.. code-block:: yaml
  :caption: CFNgin config

  stacks:
    my-stack:
      variables:
        SomeParameter: ${cfn AnotherStack.OutputName}


"""
# pylint: disable=arguments-differ
import json
import logging
from collections import namedtuple
from typing import TYPE_CHECKING, Any, Dict, Optional, Union  # pylint: disable=W

from botocore.exceptions import ClientError

from runway.cfngin.exceptions import OutputDoesNotExist, StackDoesNotExist

from .base import LookupHandler

# python2 supported pylint sees this is cyclic even though its only for type checking
# pylint: disable=cyclic-import
if TYPE_CHECKING:
    from runway.cfngin.context import (
        Context as CFNginContext,  # noqa: F401 pylint: disable=W
    )
    from runway.cfngin.providers.aws.default import (
        Provider,  # noqa: F401 pylint: disable=W
    )
    from runway.context import Context as RunwayContext  # noqa: F401 pylint: disable=W

LOGGER = logging.getLogger(__name__)
TYPE_NAME = "cfn"

OutputQuery = namedtuple("OutputQuery", ("stack_name", "output_name"))


class CfnLookup(LookupHandler):
    """CloudFormation Stack Output lookup."""

    @staticmethod
    def should_use_provider(args, provider):
        # type: (Dict[str, str], Optional['Provider']) -> bool
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
    def get_stack_output(client, query):
        """Get CloudFormation Stack output.

        Args:
            client: Boto3 CloudFormation client.
            query (OutputQuery): What to get.

        Returns:
            str: Value of the requested output.

        """
        LOGGER.debug("describing stack: %s", query.stack_name)
        stack = client.describe_stacks(StackName=query.stack_name)["Stacks"][0]
        outputs = {
            output["OutputKey"]: output["OutputValue"]
            for output in stack.get("Outputs", [])
        }
        LOGGER.debug("%s stack outputs: %s", stack["StackName"], json.dumps(outputs))
        return outputs[query.output_name]

    @classmethod
    def handle(
        cls,
        value,  # type: str
        context,  # type: Union['CFNginContext', 'RunwayContext']
        provider=None,  # type: Optional['Provider']
        **_  # type: Any
    ):
        # type: (...) -> Any
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
        except TypeError:
            raise ValueError(
                'query must be <stack-name>.<output-name>; got "{}"'.format(raw_query)
            )

        try:
            # dict is not perserved in mock call so it must be a copy of
            # args for testing to function correctly
            if cls.should_use_provider(args.copy(), provider):
                # this will only happen when used from cfngin
                result = provider.get_output(query.stack_name, query.output_name)
            else:
                cfn_client = context.get_session(region=args.get("region")).client(
                    "cloudformation"
                )
                result = cls.get_stack_output(cfn_client, query)
        except (ClientError, KeyError, StackDoesNotExist) as err:
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
            elif isinstance(err, (ClientError, StackDoesNotExist)):
                raise
            else:
                raise OutputDoesNotExist(query.stack_name, query.output_name)
        return cls.format_results(result, **args)
