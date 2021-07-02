"""Hook data lookup."""
# pyright: reportIncompatibleMethodOverride=none
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from troposphere import BaseAWSObject

from ....lookups.handlers.base import LookupHandler
from ....utils import MutableMap

if TYPE_CHECKING:
    from ....context import CfnginContext

LOGGER = logging.getLogger(__name__)
TYPE_NAME = "hook_data"


class HookDataLookup(LookupHandler):
    """Hook data lookup."""

    @classmethod
    def handle(  # pylint: disable=arguments-differ
        cls, value: str, context: CfnginContext, **_: Any
    ) -> Any:
        """Return the data from ``hook_data``.

        Args:
            value: Parameter(s) given to this lookup.
            context: Context instance.

        """
        query, args = cls.parse(value)

        hook_data = MutableMap(**context.hook_data)

        result = hook_data.find(query, args.get("default"))

        if (
            isinstance(result, BaseAWSObject)
            and args.get("get")
            and not args.get("load")
        ):
            args["load"] = "troposphere"

        if not result:
            raise ValueError(f'Could not find a value for "{value}"')

        if result == args.get("default"):
            # assume default value has already been processed so no need to
            # use these
            args.pop("load", None)
            args.pop("get", None)

        return cls.format_results(result, **args)
