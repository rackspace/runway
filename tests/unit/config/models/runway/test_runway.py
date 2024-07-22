"""Test runway.config.models.runway.__init__."""

# pyright: basic
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
    RunwayDeploymentRegionDefinitionModel,
    RunwayFutureDefinitionModel,
    RunwayModuleDefinitionModel,
    RunwayVariablesDefinitionModel,
)


class TestRunwayAssumeRoleDefinitionModel:
    """Test runway.config.models.runway.RunwayAssumeRoleDefinitionModel."""

    @pytest.mark.parametrize("arn", ["null", "none", "None", "undefined"])
    def test_convert_arn_null_value(self, arn: str) -> None:
        """Test _convert_arn_null_value."""
        assert not RunwayAssumeRoleDefinitionModel(arn=arn).arn

    def test_extra(self) -> None:
        """Test extra fields."""
        with pytest.raises(ValidationError) as excinfo:
            RunwayAssumeRoleDefinitionModel.parse_obj({"invalid": "val"})
        errors = excinfo.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("invalid",)
        assert errors[0]["msg"] == "extra fields not permitted"

    def test_field_defaults(self) -> None:
        """Test field values."""
        obj = RunwayAssumeRoleDefinitionModel()
        assert not obj.arn
        assert obj.duration == 3600
        assert not obj.post_deploy_env_revert
        assert obj.session_name == "runway"

    def test_fields(self) -> None:
        """Test fields."""
        data = {
            "arn": "test-arn",
            "duration": 900,
            "post_deploy_env_revert": True,
            "session_name": "test-session",
        }
        obj = RunwayAssumeRoleDefinitionModel.parse_obj(data)
        assert obj.arn == data["arn"]
        assert obj.duration == data["duration"]
        assert obj.post_deploy_env_revert == data["post_deploy_env_revert"]
        assert obj.session_name == data["session_name"]

    def test_string_duration(self) -> None:
        """Test duration defined as a string."""
        with pytest.raises(ValidationError) as excinfo:
            RunwayAssumeRoleDefinitionModel(duration="something")
        error = excinfo.value.errors()[0]
        assert error["loc"] == ("duration",)
        assert error["msg"] == "field can only be a string if it's a lookup"

    def test_string_duration_lookup(self) -> None:
        """Test duration defined as a lookup string."""
        value = "${var something}"
        obj = RunwayAssumeRoleDefinitionModel(duration=value)
        assert obj.duration == value

    @pytest.mark.parametrize("duration", [900, 3600, 43_200])
    def test_validate_duration(self, duration: int) -> None:
        """Test _validate_duration."""
        assert RunwayAssumeRoleDefinitionModel(duration=duration).duration == duration

    @pytest.mark.parametrize("duration", [899, 43_201])
    def test_validate_duration_invalid(self, duration: int) -> None:
        """Test _validate_duration."""
        with pytest.raises(ValidationError) as excinfo:
            RunwayAssumeRoleDefinitionModel(duration=duration)
        error = excinfo.value.errors()[0]
        assert error["loc"] == ("duration",)


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
        obj = RunwayConfigDefinitionModel.parse_obj(data)
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
        with pytest.raises(ValidationError) as excinfo:
            RunwayConfigDefinitionModel(runway_version="=latest")  # type: ignore
        assert excinfo.value.errors()[0]["msg"] == "=latest is not a valid version specifier set"

    def test_extra(self) -> None:
        """Test extra fields."""
        with pytest.raises(ValidationError) as excinfo:
            RunwayConfigDefinitionModel.parse_obj({"invalid": "val"})
        errors = excinfo.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("invalid",)
        assert errors[0]["msg"] == "extra fields not permitted"

    def test_field_defaults(self) -> None:
        """Test filed default values."""
        obj = RunwayConfigDefinitionModel()
        assert obj.deployments == []
        assert isinstance(obj.future, RunwayFutureDefinitionModel)
        assert not obj.ignore_git_branch
        assert obj.runway_version == SpecifierSet(">1.10", prereleases=True)
        assert obj.tests == []
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
        with pytest.raises(ValidationError) as excinfo:
            RunwayDeploymentDefinitionModel.parse_obj({"invalid": "val", "regions": ["us-east-1"]})
        errors = excinfo.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("invalid",)
        assert errors[0]["msg"] == "extra fields not permitted"

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
        with pytest.raises(ValidationError) as excinfo:
            RunwayDeploymentDefinitionModel.parse_obj(data)
        error = excinfo.value.errors()[0]
        assert error["loc"] == (field,)
        assert error["msg"] == "field can only be a string if it's a lookup"

        data[field] = "${var something}"
        obj = RunwayDeploymentDefinitionModel.parse_obj(data)
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
        with pytest.raises(ValidationError) as excinfo:
            RunwayDeploymentDefinitionModel(
                modules=[], parallel_regions="something", regions="something"
            )
        error = excinfo.value.errors()[0]
        assert error["loc"] == ("__root__",)
        assert error["msg"].startswith("unable to validate parallel_regions/regions")

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


class TestRunwayDeploymentRegionDefinitionModel:
    """Test runway.config.models.runway.RunwayDeploymentRegionDefinitionModel."""

    def test_extra(self) -> None:
        """Test extra fields."""
        with pytest.raises(ValidationError) as excinfo:
            RunwayDeploymentRegionDefinitionModel.parse_obj({"invalid": "val", "parallel": []})
        errors = excinfo.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("invalid",)
        assert errors[0]["msg"] == "extra fields not permitted"

    def test_fields(self) -> None:
        """Test fields."""
        assert not RunwayDeploymentRegionDefinitionModel(parallel=[]).parallel
        value = ["us-east-1", "us-west-2"]
        assert RunwayDeploymentRegionDefinitionModel(parallel=value).parallel == value

    def test_string_parallel(self) -> None:
        """Test parallel defined as a string."""
        with pytest.raises(ValidationError) as excinfo:
            RunwayDeploymentRegionDefinitionModel(parallel="something")
        error = excinfo.value.errors()[0]
        assert error["loc"] == ("parallel",)
        assert error["msg"] == "field can only be a string if it's a lookup"

    def test_string_parallel_lookup(self) -> None:
        """Test parallel defined as a lookup string."""
        value = "${var something}"
        obj = RunwayDeploymentRegionDefinitionModel(parallel=value)
        assert obj.parallel == value


class TestRunwayFutureDefinitionModel:
    """Test runway.config.models.runway.RunwayFutureDefinitionModel."""

    def test_extra(self) -> None:
        """Test extra fields."""
        with pytest.raises(ValidationError) as excinfo:
            RunwayFutureDefinitionModel.parse_obj({"invalid": "val"})
        errors = excinfo.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("invalid",)
        assert errors[0]["msg"] == "extra fields not permitted"


class TestRunwayModuleDefinitionModel:
    """Test runway.config.models.runway.RunwayModuleDefinitionModel."""

    def test_extra(self) -> None:
        """Test extra fields."""
        with pytest.raises(ValidationError) as excinfo:
            RunwayModuleDefinitionModel.parse_obj({"invalid": "val"})
        errors = excinfo.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("invalid",)
        assert errors[0]["msg"] == "extra fields not permitted"

    def test_field_defaults(self) -> None:
        """Test field defaults."""
        obj = RunwayModuleDefinitionModel()
        assert not obj.class_path
        assert obj.environments == {}
        assert obj.env_vars == {}
        assert obj.name == "undefined"
        assert obj.options == {}
        assert obj.parameters == {}
        assert obj.path == Path.cwd()
        assert obj.tags == []
        assert obj.type is None
        assert obj.parallel == []

    def test_validate_name(self) -> None:
        """Test _validate_name."""
        assert RunwayModuleDefinitionModel().name == "undefined"
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

    def test_validate_path(self) -> None:
        """Test _validate_path."""
        assert RunwayModuleDefinitionModel().path == Path.cwd()
        assert not RunwayModuleDefinitionModel(parallel=[{"path": "./"}]).path  # type: ignore
        defined_path = Path("./sampleapp.cfn")
        assert RunwayModuleDefinitionModel(path=defined_path).path == defined_path

    def test_validate_parallel(self) -> None:
        """Test _validate_parallel."""
        with pytest.raises(ValidationError) as excinfo:
            RunwayModuleDefinitionModel(
                path=Path.cwd(),
                parallel=["./"],  # type: ignore
            )
        error = excinfo.value.errors()[0]
        assert error["loc"] == ("parallel",)
        assert error["msg"] == "only one of parallel or path can be defined"

        assert RunwayModuleDefinitionModel().parallel == []
        assert RunwayModuleDefinitionModel(parallel=["./"]).parallel == [  # type: ignore
            RunwayModuleDefinitionModel(path="./")
        ]
        assert RunwayModuleDefinitionModel(
            parallel=[{"name": "test", "path": "./"}]  # type: ignore
        ).parallel == [RunwayModuleDefinitionModel(name="test", path="./")]

    @pytest.mark.parametrize("field", ["env_vars", "environments", "options", "parameters"])
    def test_fields_string_lookup_only(self, field: str) -> None:
        """Test fields that support strings only for lookups."""
        data = {field: "something"}
        with pytest.raises(ValidationError) as excinfo:
            RunwayModuleDefinitionModel.parse_obj(data)
        error = excinfo.value.errors()[0]
        assert error["loc"] == (field,)
        assert error["msg"] == "field can only be a string if it's a lookup"

        data[field] = "${var something}"
        obj = RunwayModuleDefinitionModel.parse_obj(data)
        assert obj[field] == data[field]
