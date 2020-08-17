"""Retrieve a value from SSM Parameter Store.

If the Lookup is unable to find an SSM Parameter matching the provided query,
the default value is returned or ``ParameterNotFound`` is raised if a default
value is not provided.

Parameters of type ``SecureString`` are automatically decrypted.

Parameters of type ``StringList`` are returned as a list.


.. rubric:: Arguments

This Lookup supports all :ref:`Common Lookup Arguments`.


.. rubric:: Example
.. code-block:: yaml

  deployment:
    - modules:
        - path: sampleapp.cfn
          parameters:
            secret_value: ${ssm /example/secret}
            conf_file: ${ssm /example/config/json::load=json, get=value}
            toggle: ${ssm toggle::load=yaml, get=val, transform=bool}
      env_vars:
        SOME_VARIABLE: ${ssm /example/param::region=us-east-1}
        DEFAULT_VARIABLE: ${ssm /example/default::default=default}

"""
# pylint: disable=arguments-differ
import logging
from typing import TYPE_CHECKING, Any, Union  # pylint: disable=unused-import

# using absolute for runway imports so stacker shim doesn't break when used from CFNgin
from runway.lookups.handlers.base import LookupHandler

# python2 supported pylint sees this is cyclic even though its only for type checking
# pylint: disable=cyclic-import
if TYPE_CHECKING:
    from runway.cfngin.context import (
        Context as CFNginContext,  # noqa: F401 pylint: disable=W
    )
    from runway.context import Context as RunwayContext  # noqa: F401 pylint: disable=W

LOGGER = logging.getLogger(__name__)
TYPE_NAME = "ssm"


class SsmLookup(LookupHandler):
    """SSM Parameter Store Lookup."""

    @classmethod
    def handle(cls, value, context, **_):
        # type: (str, Union['CFNginContext', 'RunwayContext'], Any) -> Any
        """Retrieve a value from SSM Parameter Store.

        Args:
            value: The value passed to the Lookup.
            context: The current context object.

        Raises:
            ParameterNotFound: Parameter not found in SSM and a default value
                was not provided.

        """
        query, args = cls.parse(value)

        session = context.get_session(region=args.get("region"))
        client = session.client("ssm")

        try:
            response = client.get_parameter(Name=query, WithDecryption=True)[
                "Parameter"
            ]
            return cls.format_results(
                response["Value"].split(",")
                if response["Type"] == "StringList"
                else response["Value"],
                **args
            )
        except client.exceptions.ParameterNotFound:
            if args.get("default"):
                args.pop("load", None)  # don't load a default value
                return cls.format_results(args.pop("default"), **args)
            raise
