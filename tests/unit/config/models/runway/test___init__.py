"""Test runway.config.models.runway.__init__."""

from pathlib import Path
from typing import Any

import pytest
import yaml
from packaging.specifiers import SpecifierSet
from pydantic import ValidationError

from runway.config.models.runway import (
    RunwayAssumeRoleDefinitionModel,
    RunwayConfigDefinitionModel,
    RunwayDeploymentDefinitionModel,
    RunwayFutureDefinitionModel,
    RunwayVariablesDefinitionModel,
)


class TestRunwayConfigDefinitionModel:
    """Test runway.config.models.runway.RunwayConfigDefinitionModel."""

    def test_add_deployment_names(self) -> None:
        """Test _add_deployment_names."""
        data = {
            "deployments": [
                {"modules": ["sampleapp.cfn"], "regions": ["us-east-1"]},
                {
                    "name": "test-name",
                    "modules": ["sampleapp.cfn"],
                    "regions": ["us-west-2"],
                },
            ]
        }
        obj = RunwayConfigDefinitionModel.model_validate(data)
        # this also adds coverage for __getitem__
        assert obj["deployments"][0]["name"] == "deployment_1"
        assert obj["deployments"][1]["name"] == "test-name"

    def test_convert_runway_version(self) -> None:
        """Test _convert_runway_version."""
        assert RunwayConfigDefinitionModel(  # handle string
            runway_version=">1.11.0"  # type: ignore
        ).runway_version == SpecifierSet(">1.11.0", prereleases=True)
        assert RunwayConfigDefinitionModel(  # handle exact version
            runway_version="1.11.0"  # type: ignore
        ).runway_version == SpecifierSet("==1.11.0", prereleases=True)
        assert RunwayConfigDefinitionModel(  # handle SpecifierSet
            runway_version=SpecifierSet(">1.11.0")  # type: ignore
        ).runway_version == SpecifierSet(">1.11.0", prereleases=True)
        assert RunwayConfigDefinitionModel(  # handle SpecifierSet
            runway_version=SpecifierSet(">1.11.0", prereleases=True)  # type: ignore
        ).runway_version == SpecifierSet(">1.11.0", prereleases=True)

    def test_convert_runway_version_invalid(self) -> None:
        """Test _convert_runway_version invalid specifier set."""
        with pytest.raises(
            ValidationError, match="Value error, =latest is not a valid version specifier set"
        ):
            RunwayConfigDefinitionModel(runway_version="=latest")  # type: ignore

    def test_extra(self) -> None:
        """Test extra fields."""
        with pytest.raises(ValidationError, match="invalid\n  Extra inputs are not permitted"):
            RunwayConfigDefinitionModel.model_validate({"invalid": "val"})

    def test_field_defaults(self) -> None:
        """Test filed default values."""
        obj = RunwayConfigDefinitionModel()
        assert obj.deployments == []
        assert isinstance(obj.future, RunwayFutureDefinitionModel)
        assert not obj.ignore_git_branch
        assert obj.runway_version is None
        assert isinstance(obj.variables, RunwayVariablesDefinitionModel)

    def test_parse_file(self, tmp_path: Path) -> None:
        """Test parse_file."""
        data = {
            "deployments": [
                {
                    "name": "test-name",
                    "modules": ["sampleapp.cfn"],
                    "regions": ["us-east-1"],
                },
            ]
        }
        runway_yml = tmp_path / "runway.yml"
        runway_yml.write_text(yaml.dump(data))

        obj = RunwayConfigDefinitionModel.parse_file(runway_yml)
        assert obj.deployments[0].modules[0].name == "sampleapp.cfn"


class TestRunwayDeploymentDefinitionModel:
    """Test runway.config.models.runway.RunwayDeploymentDefinitionModel."""

    def test_convert_simple_module(self) -> None:
        """Test _convert_simple_module."""
        obj = RunwayDeploymentDefinitionModel(
            modules=["sampleapp.cfn", {"path": "./"}],  # type: ignore
            regions=["us-east-1"],
        )
        assert obj.modules[0].path == "sampleapp.cfn"
        assert obj.modules[1].path == "./"

    def test_extra(self) -> None:
        """Test extra fields."""
        with pytest.raises(ValidationError, match="invalid\n  Extra inputs are not permitted"):
            RunwayDeploymentDefinitionModel.model_validate(
                {"invalid": "val", "regions": ["us-east-1"]}
            )

    def test_field_defaults(self) -> None:
        """Test field default values."""
        obj = RunwayDeploymentDefinitionModel(modules=[], regions=["us-east-1"])
        assert obj.account_alias is None
        assert obj.account_id is None
        assert isinstance(obj.assume_role, RunwayAssumeRoleDefinitionModel)
        assert obj.env_vars == {}
        assert obj.environments == {}
        assert obj.modules == []
        assert obj.module_options == {}
        assert obj.name == "unnamed_deployment"
        assert obj.parallel_regions == []
        assert obj.parameters == {}
        assert obj.regions == ["us-east-1"]

    @pytest.mark.parametrize(
        "field",
        [
            "env_vars",
            "environments",
            "module_options",
            "parallel_regions",
            "parameters",
            "regions",
        ],
    )
    def test_fields_string_lookup_only(self, field: str) -> None:
        """Test fields that support strings only for lookups."""
        data: dict[str, Any] = {}
        if field not in ["parallel_regions", "regions"]:
            data["regions"] = ["us-east-1"]
        data[field] = "something"
        with pytest.raises(
            ValidationError,
            match=f"{field}\n  Value error, field can only be a string if it's a lookup",
        ):
            RunwayDeploymentDefinitionModel.model_validate(data)

        data[field] = "${var something}"
        obj = RunwayDeploymentDefinitionModel.model_validate(data)
        assert obj[field] == data[field]

    def test_validate_regions(self) -> None:
        """Test _validate_regions."""
        with pytest.raises(ValidationError):
            RunwayDeploymentDefinitionModel(modules=[])
        with pytest.raises(ValidationError):
            RunwayDeploymentDefinitionModel(
                modules=[], parallel_regions=["us-east-1"], regions=["us-east-1"]
            )
        with pytest.raises(ValidationError):
            RunwayDeploymentDefinitionModel(
                modules=[],
                parallel_regions=["us-east-1"],
                regions={"parallel": ["us-east-1"]},  # type: ignore
            )
        with pytest.raises(
            ValidationError,
            match="Value error, unable to validate parallel_regions/regions - both are defined as strings",
        ):
            RunwayDeploymentDefinitionModel(
                modules=[], parallel_regions="something", regions="something"
            )

        obj0 = RunwayDeploymentDefinitionModel(modules=[], regions=["us-east-1"])
        assert obj0.regions == ["us-east-1"]
        assert obj0.parallel_regions == []

        obj1 = RunwayDeploymentDefinitionModel(modules=[], parallel_regions=["us-east-1"])
        assert obj1.regions == []
        assert obj1.parallel_regions == ["us-east-1"]

        obj2 = RunwayDeploymentDefinitionModel(
            modules=[],
            regions={"parallel": ["us-east-1"]},  # type: ignore
        )
        assert obj2.regions == []
        assert obj2.parallel_regions == ["us-east-1"]
