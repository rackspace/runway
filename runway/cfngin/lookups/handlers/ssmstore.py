"""AWS SSM Parameter Store lookup."""
# pylint: disable=arguments-differ,unused-argument
import logging
import warnings

from runway.lookups.handlers.base import LookupHandler

from ...session_cache import get_session
from ...util import read_value_from_path

LOGGER = logging.getLogger(__name__)
TYPE_NAME = "ssmstore"


class SsmstoreLookup(LookupHandler):
    """AWS SSM Parameter Store lookup."""

    DEPRECATION_MSG = "ssmstore lookup has been deprecated; use the ssm lookup instead"

    @classmethod
    def handle(cls, value, context=None, provider=None, **kwargs):
        """Retrieve (and decrypt) a parameter from AWS SSM Parameter Store.

        Args:
            value (str): Parameter(s) given to this lookup.
            context (:class:`runway.cfngin.context.Context`): Context instance.
            provider (:class:`runway.cfngin.providers.base.BaseProvider`):
                Provider instance.

        Returns:
            str: Looked up value.

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
        warnings.warn(cls.DEPRECATION_MSG, DeprecationWarning)
        LOGGER.warning(cls.DEPRECATION_MSG)

        value = read_value_from_path(value)

        region = "us-east-1"
        if "@" in value:
            region, value = value.split("@", 1)

        client = get_session(region).client("ssm")
        response = client.get_parameters(Names=[value], WithDecryption=True)
        if "Parameters" in response:
            return str(response["Parameters"][0]["Value"])

        raise ValueError(
            'SSMKey "{}" does not exist in region {}'.format(value, region)
        )
