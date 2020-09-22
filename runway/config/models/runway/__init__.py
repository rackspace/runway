"""Runway config models."""
# pylint: disable=no-self-argument,no-self-use
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from pydantic import BaseModel, Extra, root_validator, validator

from .. import utils
from ..base import ConfigProperty
from ..utils import RUNWAY_LOOKUP_STRING_ERROR, RUNWAY_LOOKUP_STRING_REGEX
from ._builtin_tests import (
    CfnLintRunwayTestArgs,
    CfnLintRunwayTestDefinitionModel,
    RunwayTestDefinitionModel,
    ScriptRunwayTestArgs,
    ScriptRunwayTestDefinitionModel,
    ValidRunwayTestTypeValues,
    YamlLintRunwayTestDefinitionModel,
)

LOGGER = logging.getLogger(__name__)

RunwayEnvironmentsType = Dict[str, Union[List[str]]]
RunwayEnvVarsType = Dict[str, Union[Dict[str, str], str]]

__all__ = [
    "RUNWAY_LOOKUP_STRING_ERROR",
    "RUNWAY_LOOKUP_STRING_REGEX",
    "CfnLintRunwayTestDefinitionModel",
    "CfnLintRunwayTestArgs",
    "RunwayAssumeRoleDefinitionModel",
    "RunwayConfigDefinitionModel",
    "RunwayDeploymentRegionDefinitionModel",
    "RunwayDeploymentDefinitionModel",
    "RunwayEnvironmentsType",
    "RunwayEnvVarsType",
    "RunwayFutureDefinitionModel",
    "RunwayModuleDefinitionModel",
    "RunwayTestDefinitionModel",
    "RunwayVariablesDefinitionModel",
    "ScriptRunwayTestDefinitionModel",
    "ScriptRunwayTestArgs",
    "ValidRunwayTestTypeValues",
    "YamlLintRunwayTestDefinitionModel",
]


class RunwayAssumeRoleDefinitionModel(ConfigProperty):
    """Model for a Runway assume role definition."""

    arn: Optional[str] = None
    duration: Union[int, str] = 3600
    post_deploy_env_revert: bool = False
    session_name: str = "runway"

    class Config:  # pylint: disable=too-few-public-methods
        """Model configuration."""

        extra = Extra.forbid

    @validator("arn")
    def _convert_arn_null_value(cls, v: Optional[str]) -> Optional[str]:  # noqa: N805
        """Convert a "nul" string into type(None)."""
        null_strings = ["null", "none", "undefined"]
        return None if isinstance(v, str) and v.lower() in null_strings else v

    @validator("duration")
    def _validate_duration(
        cls, v: Optional[Union[int, str]]  # noqa: N805
    ) -> Optional[Union[int, str]]:
        """Validate duration is within the range allowed by AWS."""
        if isinstance(v, str):
            return v
        if v < 900:
            raise ValueError("duration must be greater than or equal to 900")
        if v > 43_200:
            raise ValueError("duration must be less than or equal to 43,200")
        return v

    # TODO add regex to schema
    _validate_string_is_lookup = validator("duration", allow_reuse=True, pre=True)(
        utils.validate_string_is_lookup
    )


class RunwayDeploymentRegionDefinitionModel(ConfigProperty):
    """Model for a Runway deployment region definition."""

    parallel: Union[List[str], str]

    class Config:  # pylint: disable=too-few-public-methods
        """Model configuration."""

        extra = Extra.forbid

    # TODO add regex to schema
    _validate_string_is_lookup = validator("parallel", allow_reuse=True, pre=True)(
        utils.validate_string_is_lookup
    )


class RunwayDeploymentDefinitionModel(ConfigProperty):
    """Model for a Runway deployment definition."""

    class Config:  # pylint: disable=too-few-public-methods
        """Model configuration."""

        extra = Extra.forbid

    account_alias: Union[Dict[str, str], str] = {}
    account_id: Union[Dict[str, str], str] = {}
    assume_role: Union[str, RunwayAssumeRoleDefinitionModel] = {}
    env_vars: Union[RunwayEnvVarsType, str] = {}
    environments: Union[RunwayEnvironmentsType, str] = {}
    modules: List[RunwayModuleDefinitionModel]
    module_options: Union[Dict[str, Any], str] = {}
    name: str = "unnamed_deployment"
    parallel_regions: Union[List[str], str] = []
    parameters: Union[Dict[str, Any], str] = {}
    regions: Union[List[str], str] = []

    @root_validator(pre=True)
    def _convert_simple_module(
        cls, values: Dict[str, Any]  # noqa: N805
    ) -> Dict[str, Any]:
        """Convert simple modules to dicts."""
        modules = values.get("modules", [])
        result: List[Dict[str, Any]] = []
        for module in modules:
            if isinstance(module, str):
                result.append({"path": module})
            else:
                result.append(module)
        values["modules"] = result
        return values

    @root_validator(pre=True)
    def _validate_regions(cls, values: Dict[str, Any]) -> Dict[str, Any]:  # noqa: N805
        """Validate & simplify regions."""
        raw_regions = values.get("regions", [])
        parallel_regions = values.get("parallel_regions", [])
        if all(isinstance(i, str) for i in [raw_regions, parallel_regions]):
            raise ValueError(
                "unable to validate parallel_regions/regions - both are defined as strings"
            )
        if any(isinstance(i, str) for i in [raw_regions, parallel_regions]):
            return values  # one is a lookup so skip the remainder of the checks
        if isinstance(raw_regions, list):
            regions = raw_regions
        else:
            regions = RunwayDeploymentRegionDefinitionModel.parse_obj(raw_regions)

        if regions and parallel_regions:
            raise ValueError("only one of parallel_regions or regions can be defined")
        if not regions and not parallel_regions:
            raise ValueError("either parallel_regions or regions must be defined")

        if isinstance(regions, RunwayDeploymentRegionDefinitionModel):
            values["regions"] = []
            values["parallel_regions"] = regions.parallel
        return values

    # TODO add regex to schema
    _validate_string_is_lookup = validator(
        "env_vars",
        "environments",
        "module_options",
        "parallel_regions",
        "parameters",
        "regions",
        allow_reuse=True,
        pre=True,
    )(utils.validate_string_is_lookup)


class RunwayFutureDefinitionModel(ConfigProperty):
    """Model for the Runway future definition."""

    strict_environments: bool = False

    class Config:  # pylint: disable=too-few-public-methods
        """Model configuration."""

        extra = Extra.forbid


class RunwayModuleDefinitionModel(ConfigProperty):
    """Model for a Runway module definition."""

    class_path: Optional[str] = None
    env_vars: Union[RunwayEnvVarsType, str] = {}
    environments: Union[RunwayEnvironmentsType, str] = {}
    name: str
    options: Union[Dict[str, Any], str] = {}
    parameters: Union[Dict[str, Any], str] = {}
    path: Optional[
        Union[str, Path]
    ] = None  # supports variables so won't be Path to start
    tags: List[str] = []
    type: Optional[str] = None  # TODO add enum
    # needs to be last
    parallel: List[RunwayModuleDefinitionModel] = []

    class Config:  # pylint: disable=too-few-public-methods
        """Model configuration."""

        extra = Extra.forbid

    @root_validator(pre=True)
    def _validate_name(cls, values: Dict[str, Any]) -> Dict[str, Any]:  # noqa: N805
        """Validate module name."""
        if "name" in values:
            return values
        if "parallel" in values:
            values["name"] = "parallel_parent"
            return values
        if "path" in values:
            values["name"] = Path(values["path"]).resolve().name
            return values
        values["name"] = "undefined"
        return values

    @root_validator(pre=True)
    def _validate_path(cls, values):  # noqa: N805
        """Validate path and sets a default value if needed."""
        if not values.get("path") and not values.get("parallel"):
            values["path"] = Path.cwd()
        return values

    @validator("parallel", pre=True)
    def _validate_parallel(
        cls, v: List[Union[Dict[str, Any], str]], values: Dict[str, Any],  # noqa: N805
    ) -> List[Dict[str, Any]]:
        """Validate parallel."""
        if v and values.get("path"):
            raise ValueError("only one of parallel or path can be defined")
        result = []
        for mod in v:
            if isinstance(mod, str):
                result.append({"path": mod})
            else:
                result.append(mod)
        return result

    # TODO add regex to schema
    _validate_string_is_lookup = validator(
        "env_vars", "environments", "options", "parameters", allow_reuse=True, pre=True,
    )(utils.validate_string_is_lookup)


# https://pydantic-docs.helpmanual.io/usage/postponed_annotations/#self-referencing-models
RunwayModuleDefinitionModel.update_forward_refs()


class RunwayVariablesDefinitionModel(ConfigProperty):
    """Model for a Runway variable definition."""

    file_path: Optional[Path]
    sys_path: Path = Path.cwd()

    class Config:  # pylint: disable=too-few-public-methods
        """Model configuration."""

        extra = Extra.allow

    _convert_null_values = validator("*", allow_reuse=True)(utils.convert_null_values)


class RunwayConfigDefinitionModel(BaseModel):
    """Runway configuration definition model."""

    deployments: List[RunwayDeploymentDefinitionModel]
    future: RunwayFutureDefinitionModel = RunwayFutureDefinitionModel()
    ignore_git_branch: bool = False
    runway_version: Optional[Union[str, SpecifierSet]] = SpecifierSet(
        ">1.10", prereleases=True
    )
    tests: List[RunwayTestDefinitionModel] = []
    variables: RunwayVariablesDefinitionModel = RunwayVariablesDefinitionModel()

    class Config:  # pylint: disable=too-few-public-methods
        """Model configuration."""

        arbitrary_types_allowed = True
        extra = Extra.forbid
        title = "Runway Configuration File"
        validate_all = True
        validate_assignment = True

    @root_validator(pre=True)
    def _add_deployment_names(
        cls, values: Dict[str, Any]  # noqa: N805
    ) -> Dict[str, Any]:
        """Add names to deployments that are missing them."""
        deployments = values.get("deployments", [])
        for i, deployment in enumerate(deployments):
            if not deployment.get("name"):
                deployment["name"] = f"deployment_{i + 1}"
        values["deployments"] = deployments
        return values

    @validator("runway_version")
    def _convert_runway_version(
        cls, v: Optional[Union[str, SpecifierSet]]  # noqa: N805
    ) -> SpecifierSet:
        """Convert runway_version string into SpecifierSet with some value handling.

        Args:
            v: The value to be converted/validated.

        Raises:
            ValueError: The provided value is not a valid version specifier set.

        """
        if isinstance(v, SpecifierSet) or not v:
            return v
        try:
            return SpecifierSet(v, prereleases=True)
        except InvalidSpecifier:
            if any(v.startswith(i) for i in ["!", "~", "<", ">", "="]):
                raise ValueError(f"{v} is not a valid version specifier set") from None
            LOGGER.debug(
                "runway_version is not a valid version specifier; trying as an exact version",
                exc_info=True,
            )
            return SpecifierSet("==" + v, prereleases=True)

    @classmethod
    def parse_file(cls, path: Path) -> RunwayConfigDefinitionModel:
        """Parse a file."""
        return cls.parse_raw(path.read_text())

    @classmethod
    def parse_raw(cls, data: str) -> RunwayConfigDefinitionModel:
        """Parse raw data."""
        return cls.parse_obj(yaml.safe_load(data))

    def __getitem__(self, key: str) -> Any:
        """Implement evaluation of self[key].

        Args:
            key: Attribute name to return the value for.

        Returns:
            The value associated with the provided key/attribute name.

        Raises:
            AttributeError: If attribute does not exist on this object.

        """
        return getattr(self, key)


# https://pydantic-docs.helpmanual.io/usage/postponed_annotations/#self-referencing-models
RunwayDeploymentDefinitionModel.update_forward_refs()
