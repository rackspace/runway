"""Test runway.config.models.runway._future."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from runway.config.models.runway._future import RunwayFutureDefinitionModel


class TestRunwayFutureDefinitionModel:
    """Test RunwayFutureDefinitionModel."""

    def test_extra(self) -> None:
        """Test extra fields."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            RunwayFutureDefinitionModel.model_validate({"invalid": "val"})
