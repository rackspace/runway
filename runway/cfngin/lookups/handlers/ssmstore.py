"""AWS SSM Parameter Store lookup."""
# pyright: reportIncompatibleMethodOverride=none
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ....lookups.handlers.base import LookupHandler
from ...util import read_value_from_path

if TYPE_CHECKING:
    from ....context.cfngin import CfnginContext

LOGGER = logging.getLogger(__name__)
TYPE_NAME = "ssmstore"


class SsmstoreLookup(LookupHandler):
    """AWS SSM Parameter Store lookup."""

    DEPRECATION_MSG = "ssmstore lookup has been deprecated; use the ssm lookup instead"

    @classmethod
    def handle(  # pylint: disable=arguments-differ
        cls, value: str, context: CfnginContext, **_: Any
    ) -> str:
        """Retrieve (and decrypt) a parameter from AWS SSM Parameter Store.

        Args:
            value: Parameter(s) given to this lookup.
            context: Context instance.

        ``value`` should be in the following format::

            [<region>@]ssmkey

        .. note:: The region is optional, and defaults to us-east-1 if not given.

        Example:
            ::

                # In CFNgin we would reference the encrypted value like:
                conf_key: ${ssmstore us-east-1@ssmkey}

            You can optionally store the value in a file, ie::

                ssmstore_value.txt
                us-east-1@ssmkey

            and reference it within CFNgin (NOTE: the path should be relative
            to the CFNgin config file)::

                conf_key: ${ssmstore file://ssmstore_value.txt}

                # Both of the above would resolve to
                conf_key: PASSWORD

        """
        LOGGER.warning(cls.DEPRECATION_MSG)

        value = read_value_from_path(value)

        region = "us-east-1"
        if "@" in value:
            region, value = value.split("@", 1)

        client = context.get_session(region=region).client("ssm")
        response = client.get_parameters(Names=[value], WithDecryption=True)
        if "Parameters" in response:
            return str(response["Parameters"][0]["Value"])

        raise ValueError(
            'SSMKey "{}" does not exist in region {}'.format(value, region)
        )
