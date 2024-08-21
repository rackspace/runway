"""Retrieve a variable from the variables file or definition."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

from .base import LookupHandler

if TYPE_CHECKING:

    from ...utils import MutableMap


LOGGER = logging.getLogger(__name__)
TYPE_NAME = "var"


class VarLookup(LookupHandler[Any]):
    """Variable definition Lookup."""

    TYPE_NAME: ClassVar[str] = "var"
    """Name that the Lookup is registered as."""

    @classmethod
    def handle(cls, value: str, *_args: Any, variables: MutableMap, **_kwargs: Any) -> Any:
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
