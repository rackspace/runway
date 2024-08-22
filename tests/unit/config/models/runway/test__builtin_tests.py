"""Test runway.config.models.runway._builtin_tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from runway.config.models.runway import RunwayTestDefinitionModel


class TestRunwayTestDefinitionModel:
    """Test runway.config.models.runway._builtin_tests.RunwayTestDefinitionModel."""

    def test_invalid_type(self) -> None:
        """Test invalid type."""
        with pytest.raises(ValidationError) as excinfo:
            RunwayTestDefinitionModel.model_validate({"type": "invalid"})
        assert excinfo.value.errors()[0]["loc"] == ("type",)

    @pytest.mark.parametrize("required", [None, True, False])
    def test_required(self, required: bool | None) -> None:
        """Test required."""
        if isinstance(required, bool):
            obj = RunwayTestDefinitionModel(type="script", required=required)
            assert obj.required is required
        else:
            obj = RunwayTestDefinitionModel(type="script")
            assert obj.required is False

    def test_string_args(self) -> None:
        """Test args defined as a string."""
        with pytest.raises(
            ValidationError,
            match="args\n  Value error, field can only be a string if it's a lookup",
        ):
            RunwayTestDefinitionModel.model_validate({"args": "something", "type": "yamllint"})

    def test_string_args_lookup(self) -> None:
        """Test args defined as a lookup string."""
        data = {"args": "${var something}", "type": "yamllint"}
        obj = RunwayTestDefinitionModel.model_validate(data)
        assert obj.args == data["args"]

    def test_string_required(self) -> None:
        """Test required defined as a string."""
        with pytest.raises(
            ValidationError,
            match="required\n  Value error, field can only be a string if it's a lookup",
        ):
            RunwayTestDefinitionModel.model_validate({"required": "something", "type": "yamllint"})

    def test_string_required_lookup(self) -> None:
        """Test required defined as a lookup string."""
        data = {"required": "${var something}", "type": "yamllint"}
        obj = RunwayTestDefinitionModel.model_validate(data)
        assert obj.required == data["required"]
