"""Test runway.config.components.runway._test_def."""

import pytest
from pydantic import ValidationError

from runway.config.components.runway import RunwayTestDefinition


class TestRunwayTestDefinition:
    """Test runway.config.components.runway._test_def.RunwayTestDefinition."""

    def test_new_invalid(self) -> None:
        """Test new invalid type."""
        with pytest.raises(ValidationError, match="Input should be a valid dictionary or instance"):
            RunwayTestDefinition.parse_obj([])

    def test_parse_obj_invalid(self) -> None:
        """Test parse_obj invalid object."""
        with pytest.raises(ValidationError):
            RunwayTestDefinition.parse_obj({"type": "invalid"})

    def test_register_variable(self) -> None:
        """Test _register_variable."""
        obj = RunwayTestDefinition.parse_obj(
            {"type": "script", "name": "test_register_variable", "required": True}
        )
        assert obj._vars["required"].name == "test_register_variable.required"
