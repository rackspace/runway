"""Test runway.config.models.runway._deployment_region."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from runway.config.models.runway._region import RunwayDeploymentRegionDefinitionModel


class TestRunwayDeploymentRegionDefinitionModel:
    """Test RunwayDeploymentRegionDefinitionModel."""

    def test_extra(self) -> None:
        """Test extra fields."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            RunwayDeploymentRegionDefinitionModel.model_validate({"invalid": "val", "parallel": []})

    def test_fields(self) -> None:
        """Test fields."""
        assert not RunwayDeploymentRegionDefinitionModel(parallel=[]).parallel
        value = ["us-east-1", "us-west-2"]
        assert RunwayDeploymentRegionDefinitionModel(parallel=value).parallel == value

    def test_string_parallel(self) -> None:
        """Test parallel defined as a string."""
        with pytest.raises(
            ValidationError,
            match="parallel\n  Value error, field can only be a string if it's a lookup",
        ):
            RunwayDeploymentRegionDefinitionModel(parallel="something")

    def test_string_parallel_lookup(self) -> None:
        """Test parallel defined as a lookup string."""
        value = "${var something}"
        obj = RunwayDeploymentRegionDefinitionModel(parallel=value)
        assert obj.parallel == value
