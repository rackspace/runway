"""Tests for lookup handler for var."""

# pyright: basic
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from runway.lookups.handlers.var import VarLookup
from runway.utils import MutableMap

if TYPE_CHECKING:
    from ...factories import MockRunwayContext

VARIABLES = MutableMap(**{"str_val": "test", "false_val": False})


class TestVarLookup:
    """Tests for VarLookup."""

    def test_handle(self, runway_context: MockRunwayContext) -> None:
        """Validate handle base functionality."""
        assert VarLookup.handle("str_val", context=runway_context, variables=VARIABLES) == "test"

    def test_handle_false_result(self, runway_context: MockRunwayContext) -> None:
        """Validate that a bool value of False can be resolved."""
        assert not VarLookup.handle("false_val", context=runway_context, variables=VARIABLES)

    def test_handle_not_found(self, runway_context: MockRunwayContext) -> None:
        """Validate exception when lookup cannot be resolved."""
        with pytest.raises(ValueError):
            VarLookup.handle("NOT_VALID", context=runway_context, variables=VARIABLES)
