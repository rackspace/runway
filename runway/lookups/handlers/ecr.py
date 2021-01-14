"""Retrieve a value from AWS Elastic Container Registry (ECR).

This Lookup only supports very specific queries.

Supported Queries
-----------------

login-password
^^^^^^^^^^^^^^

Get a password to login to ECR registry.

The returned value can be passed to the login command of the container
client of your preference, such as the :ref:`Docker CFNgin hook <cfngin.hooks.docker>`.
After you have authenticated to an Amazon ECR registry with this Lookup,
you can use the client to push and pull images from that registry as long
as your IAM principal has access to do so until the token expires.
The authorization token is valid for **12 hours**.

.. rubric:: Arguments

This Lookup does not support any arguments.

.. rubric:: Example
.. code-block:: yaml
    :caption: runway.yml

    deployments:
      - modules:
          - path: example.cfn
            parameters:
              ecr_password: ${ecr login-password}
        ...

.. code-block:: yaml
    :caption: cfngin.yml

    pre_build:
      - path: runway.cfngin.hooks.docker.login
        args:
          password: ${ecr login-password}
          ...

"""
# pylint: disable=arguments-differ
import base64
import logging
from typing import TYPE_CHECKING, Any, Union  # pylint: disable=W

# using absolute for runway imports so stacker shim doesn't break when used from CFNgin
from runway.lookups.handlers.base import LookupHandler

# python2 supported pylint sees this is cyclic even though its only for type checking
# pylint: disable=cyclic-import
if TYPE_CHECKING:
    from mypy_boto3_ecr.client import ECRClient  # pylint: disable=E

    from runway.cfngin.context import (
        Context as CFNginContext,  # noqa: F401 pylint: disable=W
    )
    from runway.context import Context as RunwayContext  # noqa: F401 pylint: disable=W

LOGGER = logging.getLogger(__name__)

TYPE_NAME = "ecr"


class EcrLookup(LookupHandler):
    """ECR Lookup."""

    @staticmethod
    def get_login_password(client):  # type: (ECRClient) -> str
        """Get a password to login to ECR registry."""
        auth = client.get_authorization_token()["authorizationData"][0]
        auth_token = base64.b64decode(auth["authorizationToken"]).decode()
        _, password = auth_token.split(":")
        return password

    @classmethod
    def handle(cls, value, context, **_):
        # type: (str, Union['CFNginContext', 'RunwayContext'], Any) -> Any
        """Retrieve a value from AWS Elastic Container Registry (ECR).

        Args:
            value: The value passed to the Lookup.
            context: The current context object.

        """
        query, args = cls.parse(value)

        session = context.get_session(region=args.get("region"))
        client = session.client("ecr")

        if query == "login-password":
            result = cls.get_login_password(client)
        else:
            raise ValueError("ecr lookup does not support '{}'".format(query))
        return cls.format_results(result, **args)
