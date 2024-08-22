"""Test runway.config.models.runway._module."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from runway.config.models.runway._module import RunwayModuleDefinitionModel


class TestRunwayModuleDefinitionModel:
    """Test rRunwayModuleDefinitionModel."""

    def test__validate_name(self) -> None:
        """Test _validate_name."""
        assert RunwayModuleDefinitionModel().name == "runway"
        assert RunwayModuleDefinitionModel(name="test-name").name == "test-name"
        assert (
            RunwayModuleDefinitionModel(parallel=[{"path": "./"}]).name  # type: ignore
            == "parallel_parent"
        )
        assert (
            RunwayModuleDefinitionModel(
                name="something",
                parallel=[{"path": "./"}],  # type: ignore
            ).name
            == "something"
        )
        assert RunwayModuleDefinitionModel(path="./").name == Path.cwd().resolve().name

    def test__validate_parallel(self) -> None:
        """Test _validate_parallel."""
        with pytest.raises(
            ValidationError,
            match="parallel\n  Value error, only one of parallel or path can be defined",
        ):
            RunwayModuleDefinitionModel(
                path=Path.cwd(),
                parallel=["./"],  # type: ignore
            )

        assert RunwayModuleDefinitionModel().parallel == []
        assert RunwayModuleDefinitionModel(parallel=["./"]).parallel == [  # type: ignore
            RunwayModuleDefinitionModel(path="./")
        ]
        assert RunwayModuleDefinitionModel(
            parallel=[{"name": "test", "path": "./"}]  # type: ignore
        ).parallel == [RunwayModuleDefinitionModel(name="test", path="./")]

    def test__validate_path(self) -> None:
        """Test _validate_path."""
        assert RunwayModuleDefinitionModel().path == Path.cwd()
        assert not RunwayModuleDefinitionModel(parallel=[{"path": "./"}]).path  # type: ignore
        defined_path = Path("./sampleapp.cfn")
        assert RunwayModuleDefinitionModel(path=defined_path).path == defined_path

    @pytest.mark.parametrize("field", ["env_vars", "environments", "options", "parameters"])
    def test__validate_string_is_lookup(self, field: str) -> None:
        """Test fields that support strings only for lookups."""
        data = {field: "something"}
        with pytest.raises(
            ValidationError,
            match=f"{field}\n  Value error, field can only be a string if it's a lookup",
        ):
            RunwayModuleDefinitionModel.model_validate(data)

        data[field] = "${var something}"
        obj = RunwayModuleDefinitionModel.model_validate(data)
        assert obj[field] == data[field]

    def test_extra(self) -> None:
        """Test extra fields."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            RunwayModuleDefinitionModel.model_validate({"invalid": "val"})

    def test_field_defaults(self) -> None:
        """Test field defaults."""
        obj = RunwayModuleDefinitionModel()
        assert not obj.class_path
        assert obj.environments == {}
        assert obj.env_vars == {}
        assert obj.name == "runway"
        assert obj.options == {}
        assert obj.parameters == {}
        assert obj.path == Path.cwd()
        assert obj.tags == []
        assert obj.type is None
        assert obj.parallel == []
