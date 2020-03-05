"""Retrieve a value from SSM Parameter Store."""
# pylint: disable=arguments-differ
import logging
from typing import TYPE_CHECKING, Any, Union  # pylint: disable=unused-import

# using absolute for runway imports so stacker shim doesn't break when used from CFNgin
from runway.lookups.handlers.base import LookupHandler

# python2 supported pylint sees this is cyclic even though its only for type checking
# pylint: disable=cyclic-import
if TYPE_CHECKING:
    from runway.context import Context as RunwayContext  # noqa: F401 pylint: disable=W
    from runway.cfngin.context import Context as CFNginContext  # noqa: F401 pylint: disable=W

LOGGER = logging.getLogger(__name__)
TYPE_NAME = 'ssm'


class SsmLookup(LookupHandler):
    """SSM Parameter Store lookup."""

    @classmethod
    def handle(cls, value, context, **_):
        # type: (str, Union['CFNginContext', 'RunwayContext'], Any) -> Any
        """Retrieve a value from SSM Parameter Store."""
        query, args = cls.parse(value)

        session = context.get_session(region=args.get('region'))
        client = session.client('ssm')

        try:
            response = client.get_parameter(
                Name=query,
                WithDecryption=True
            )['Parameter']
            return cls.format_results(response['Value'].split(',')
                                      if response['Type'] == 'StringList'
                                      else response['Value'], **args)
        except client.exceptions.ParameterNotFound:
            if args.get('default'):
                args.pop('load', None)  # don't load a default value
                return cls.format_results(args.pop('default'), **args)
            raise
