"""Retrieve a value from SSM Parameter Store."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

from ...lookups.handlers.base import LookupHandler

if TYPE_CHECKING:
    from mypy_boto3_ssm.type_defs import ParameterTypeDef

    from ...context import CfnginContext, RunwayContext

LOGGER = logging.getLogger(__name__)


class SsmLookup(LookupHandler["CfnginContext | RunwayContext"]):
    """SSM Parameter Store Lookup."""

    TYPE_NAME: ClassVar[str] = "ssm"
    """Name that the Lookup is registered as."""

    @classmethod
    def handle(cls, value: str, context: CfnginContext | RunwayContext, **_kwargs: Any) -> Any:
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
            return cls.format_results(
                cls._handle_get_parameter(
                    client.get_parameter(Name=query, WithDecryption=True)["Parameter"]
                ),
                **args,
            )
        except client.exceptions.ParameterNotFound:
            if args.get("default"):
                args.pop("load", None)  # don't load a default value
                return cls.format_results(args.pop("default"), **args)
            raise

    @staticmethod
    def _handle_get_parameter(parameter: ParameterTypeDef) -> list[str] | str | None:
        """Handle the return value of ``get_parameter``."""
        if "Value" not in parameter:
            return None
        value = parameter["Value"]
        if parameter.get("Type") == "StringList":
            return value.split(",")
        return value
