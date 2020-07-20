"""Retrieve a value from CloudFormation Stack outputs."""
# pylint: disable=arguments-differ
import logging
import json
from collections import namedtuple
from typing import TYPE_CHECKING, Any, Dict, Optional, Union  # pylint: disable=W

from .base import LookupHandler
from runway.cfngin.exceptions import OutputDoesNotExist

# python2 supported pylint sees this is cyclic even though its only for type checking
# pylint: disable=cyclic-import
if TYPE_CHECKING:
    from runway.context import Context as RunwayContext  # noqa: F401 pylint: disable=W
    from runway.cfngin.context import Context as CFNginContext  # noqa: F401 pylint: disable=W
    from runway.cfngin.providers.aws.default import Provider

LOGGER = logging.getLogger(__name__)
TYPE_NAME = "cfn"

OutputQuery = namedtuple('OutputQuery', ('stack_name', 'output_name'))
OutputQuery.__doc__ = """Named tuple representing the query for a Stack output.

Attrs:
    stack_name (str): CloudFormation Stack name.
    output_name (str): CloudFormation Stack output name.

"""


class CfnLookup(LookupHandler):
    """CloudFormation Stack output lookup."""

    @staticmethod
    def should_use_provider(args, provider):
        # type: (Dict[str, str], Optional['Provider']) -> bool
        """Determine if the provider should be used for the lookup."""
        if provider:
            if args.get('region') and provider.region != args['region']:
                LOGGER.debug('not using provider; requested region does not match')
                return False
            LOGGER.debug('using provider')
            return True
        return False

    @staticmethod
    def get_stack_output(client, query):
        """Get CloudFormation Stack output.

        Args:
            client: Boto3 CloudFormation client.
            query: What to get.

        Returns:
            str: Value of the requested output.

        Raises:
            OutputDoesNotExist: Output could not be found on the Stack.

        """
        stack = client.describe_stacks(StackName=query.stack_name)['Stacks'][0]
        outputs = {
            output['OutputKey']: output['OutputValue']
            for output in stack.get('Outputs', [])
        }
        LOGGER.debug('stack outputs:\n%s', json.dumps(outputs))
        return outputs[query.output_name]

    @classmethod
    def handle(cls,
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

        """
        raw_query, args = cls.parse(value)
        try:
            query = OutputQuery(*raw_query.split('.'))
        except ValueError:
            raise ValueError(
                'query must be <stack-name>.<output-name>; got ' + raw_query
            )

        try:
            if cls.should_use_provider(args, provider):
                result = provider.get_output(query.stack_name, query.output_name)
            else:
                cfn_client = context.get_session(region=args.get('region')) \
                    .client('cloudformation')
                result = cls.get_stack_output(cfn_client, query)
        except KeyError:
            if 'default' in args:
                args.pop('load')  # don't load a default value
                result = args.pop('default')
            else:
                raise OutputDoesNotExist(query.stack_name, query.output_name)
        return cls.format_results(result, **args)
