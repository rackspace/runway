"""Retrieve a variable from the variables file or definition."""
# pyright: reportIncompatibleMethodOverride=none
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from typing_extensions import Final, Literal

from .base import LookupHandler

if TYPE_CHECKING:
    from ...utils import MutableMap


LOGGER = logging.getLogger(__name__)
TYPE_NAME = "var"


class VarLookup(LookupHandler):
    """Variable definition Lookup."""

    TYPE_NAME: Final[Literal["var"]] = "var"
    """Name that the Lookup is registered as."""

    @classmethod
    def handle(  # pylint: disable=arguments-differ
        cls, value: str, *__args: Any, variables: MutableMap, **__kwargs: Any
    ) -> Any:
        """Retrieve a variable from the variable definition.

        The value is retrieved from the variables passed to Runway using
        either a variables file or the ``variables`` directive of the
        config file.

        Args:
            value: The value passed to the Lookup.
            variables: The resolved variables pass to Runway.

        Raises:
            ValueError: Unable to find a value for the provided query and
                a default value was not provided.

        """
        query, args = cls.parse(value)

        result = variables.find(query, default=args.pop("default", ""))

        if result != "":  # allows for False bool and NoneType results
            return cls.format_results(result, **args)

        raise ValueError(f'"{query}" does not exist in the variable definition')
