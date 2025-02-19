"""Retrieve a value from AWS Elastic Container Registry (ECR)."""

from __future__ import annotations

import base64
import logging
from typing import TYPE_CHECKING, Any, ClassVar, cast

from ...lookups.handlers.base import LookupHandler

if TYPE_CHECKING:
    from mypy_boto3_ecr.client import ECRClient

    from ...context import CfnginContext, RunwayContext

LOGGER = logging.getLogger(__name__)


class EcrLookup(LookupHandler["CfnginContext | RunwayContext"]):
    """ECR Lookup."""

    TYPE_NAME: ClassVar[str] = "ecr"
    """Name that the Lookup is registered as."""

    @staticmethod
    def get_login_password(client: ECRClient) -> str:
        """Get a password to login to ECR registry."""
        auth = client.get_authorization_token().get("authorizationData", [None])[0]
        if not auth or "authorizationToken" not in auth:
            raise ValueError("get_authorization_token did not return authorizationData")
        auth_token = base64.b64decode(auth["authorizationToken"]).decode()
        _, password = auth_token.split(":")
        return password

    @classmethod
    def handle(cls, value: str, context: CfnginContext | RunwayContext, **_kwargs: Any) -> Any:
        """Retrieve a value from AWS Elastic Container Registry (ECR).

        Args:
            value: The value passed to the Lookup.
            context: The current context object.

        """
        query, args = cls.parse(value)

        session = context.get_session(region=cast("str | None", args.get("region")))
        client = session.client("ecr")

        if query == "login-password":
            result = cls.get_login_password(client)
        else:
            raise ValueError(f"ecr lookup does not support '{query}'")
        return cls.format_results(result, **args)
