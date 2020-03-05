"""Retrieve a value from SSM Parameter Store."""
# pylint: disable=arguments-differ
import logging
from typing import Any, Union, TYPE_CHECKING  # pylint: disable=unused-import

# using absolute for runway imports so stacker shim doesn't break when used from CFNgin
from runway.lookups.handlers.base import LookupHandler
# from runway.util import MutableMap

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
        response = client.get_parameters(
            Names=[query],
            WithDecryption=True
        ).get('Parameters', [])[0]

        if not response:
            raise ValueError(
                'SSM Parameter "{}" does not exist in region {}'.format(
                    value, session.region_name))

        return cls.format_results(response['Value'].split(',')
                                  if response['Type'] == 'StringList'
                                  else response['Value'], **args)
