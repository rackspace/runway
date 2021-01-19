"""Tests for lookup registry and common lookup functionality."""
# pylint: disable=no-self-use
from __future__ import annotations

from typing import TYPE_CHECKING

from runway.lookups.registry import RUNWAY_LOOKUP_HANDLERS
from runway.util import MutableMap

if TYPE_CHECKING:
    from ..factories import MockRunwayContext

VALUES = {"str_val": "test"}
CONTEXT = MutableMap(**{"env_vars": VALUES})
VARIABLES = MutableMap(**VALUES)


class TestCommonLookupFunctionality:
    """Test common lookup functionally.

    All lookup handles should be able to pass these tests. Handling must
    be implement in all lookups in the "handle" method using the provided
    class methods of the "LookupHandler" base class.

    """

    def test_handle_default(self, runway_context: MockRunwayContext) -> None:
        """Verify default value is handled by lookups."""
        lookup_handlers = RUNWAY_LOOKUP_HANDLERS.copy()
        lookup_handlers.pop("cfn")  # requires special testing
        lookup_handlers.pop("ecr")  # requires special testing
        lookup_handlers.pop("ssm")  # requires special testing
        for _, lookup in lookup_handlers.items():
            result = lookup.handle(
                "NOT_VALID::default=default value",
                context=runway_context,
                variables=VARIABLES,
            )

            assert result == "default value"

    def test_handle_transform(self, runway_context: MockRunwayContext) -> None:
        """Verify transform is handled by lookup."""
        lookup_handlers = RUNWAY_LOOKUP_HANDLERS.copy()
        lookup_handlers.pop("cfn")  # requires special testing
        lookup_handlers.pop("ecr")  # requires special testing
        lookup_handlers.pop("ssm")  # requires special testing
        runway_context.env.vars.update(VALUES)

        for _, lookup in lookup_handlers.items():
            result = lookup.handle(
                "NOT_VALID::default=false, transform=bool",
                context=runway_context,
                variables=VARIABLES,
            )

            assert not result
