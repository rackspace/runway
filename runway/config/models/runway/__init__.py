"""Runway config models."""

from __future__ import annotations

import locale
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, TypeVar, cast

import yaml
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from pydantic import (
    ConfigDict,
    Field,
    GetCoreSchemaHandler,
    GetJsonSchemaHandler,
    field_serializer,
    field_validator,
    model_validator,
)
from pydantic_core import CoreSchema, core_schema

from ....utils.pydantic_validators import LaxStr
from .. import utils
from ..base import ConfigProperty
from ..utils import RUNWAY_LOOKUP_STRING_ERROR, RUNWAY_LOOKUP_STRING_REGEX
from ._assume_role import RunwayAssumeRoleDefinitionModel
from ._builtin_tests import RunwayTestDefinitionModel, ValidRunwayTestTypeValues
from ._future import RunwayFutureDefinitionModel
from ._module import RunwayModuleDefinitionModel
from ._region import RunwayDeploymentRegionDefinitionModel
from ._type_defs import (
    RunwayEnvironmentsType,
    RunwayEnvironmentsUnresolvedType,
    RunwayEnvVarsType,
    RunwayEnvVarsUnresolvedType,
    RunwayModuleTypeTypeDef,
)
from ._variables import RunwayVariablesDefinitionModel

if TYPE_CHECKING:
    from pydantic import BaseModel
    from pydantic.json_schema import JsonSchemaValue
    from typing_extensions import Self

    Model = TypeVar("Model", bound=BaseModel)

LOGGER = logging.getLogger(__name__)


__all__ = [
    "RUNWAY_LOOKUP_STRING_ERROR",
    "RUNWAY_LOOKUP_STRING_REGEX",
    "RunwayAssumeRoleDefinitionModel",
    "RunwayConfigDefinitionModel",
    "RunwayDeploymentDefinitionModel",
    "RunwayDeploymentRegionDefinitionModel",
    "RunwayEnvVarsType",
    "RunwayEnvVarsUnresolvedType",
    "RunwayEnvironmentsType",
    "RunwayEnvironmentsUnresolvedType",
    "RunwayFutureDefinitionModel",
    "RunwayModuleDefinitionModel",
    "RunwayModuleTypeTypeDef",
    "RunwayTestDefinitionModel",
    "RunwayVariablesDefinitionModel",
    "RunwayVersionField",
    "ValidRunwayTestTypeValues",
]


def _deployment_json_schema_extra(schema: dict[str, Any]) -> None:
    """Process the schema after it has been generated.

    Schema is modified in place. Return value is ignored.

    https://pydantic-docs.helpmanual.io/usage/schema/#schema-customization

    """
    schema["description"] = "A collection of modules, regions, and other configurations to deploy."
    # modify schema to allow simple string or mapping definition for a module
    module_ref = schema["properties"]["modules"]["items"].pop("$ref")
    schema["properties"]["modules"]["items"]["anyOf"] = [
        {"$ref": module_ref},
        {"type": "string"},
    ]


class RunwayDeploymentDefinitionModel(ConfigProperty):
    """Model for a Runway deployment definition."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra=_deployment_json_schema_extra,
        title="Runway Deployment Definition",
        validate_default=True,
        validate_assignment=True,
    )

    account_alias: Annotated[
        str | None,
        Field(
            description="Used to verify the currently assumed role or credentials. "
            "(supports lookups)",
            examples=["example-alias", "${var alias.${env DEPLOY_ENVIRONMENT}}"],
        ),
    ] = None
    """Used to verify the currently assumed role or credentials. (supports lookups)"""

    account_id: Annotated[
        str | None,
        LaxStr,
        Field(
            description="Used to verify the currently assumed role or credentials. "
            "(supports lookups)",
            examples=["123456789012", "${var id.${env DEPLOY_ENVIRONMENT}}"],
        ),
    ] = None
    """Used to verify the currently assumed role or credentials. (supports lookups)"""

    assume_role: Annotated[
        str | RunwayAssumeRoleDefinitionModel | None,
        Field(
            description="Assume a role when processing the deployment. (supports lookups)",
            examples=[
                "arn:aws:iam::123456789012:role/name",
                *cast(
                    "dict[str, list[str]]",
                    RunwayAssumeRoleDefinitionModel.model_config.get("json_schema_extra", {}),
                ).get("examples", []),
            ],
        ),
    ] = RunwayAssumeRoleDefinitionModel()
    """Assume a role when processing the deployment. (supports lookups)"""

    env_vars: Annotated[
        RunwayEnvVarsUnresolvedType,
        Field(
            title="Environment Variables",
            description="Additional variables to add to the environment when "
            "processing the deployment. (supports lookups)",
            examples=[
                "${var env_vars.${env DEPLOY_ENVIRONMENT}}",
                {
                    "EXAMPLE_VARIABLE": "value",
                    "KUBECONFIG": [".kube", "${env DEPLOY_ENVIRONMENT}", "config"],
                },
            ],
        ),
    ] = {}
    """Additional variables to add to the environment when processing the deployment. (supports lookups)"""

    environments: Annotated[
        RunwayEnvironmentsUnresolvedType,
        Field(
            description="Explicitly enable/disable the deployment for a specific "
            "deploy environment, AWS Account ID, and AWS Region combination. "
            "Can also be set as a static boolean value. (supports lookups)",
            examples=[
                "${var envs.${env DEPLOY_ENVIRONMENT}}",
                {"dev": "123456789012", "prod": "us-east-1"},
                {"dev": True, "prod": False},
                {"dev": ["us-east-1"], "prod": ["us-west-2", "ca-central-1"]},
                {
                    "dev": ["123456789012/us-east-1", "123456789012/us-west-2"],
                    "prod": ["234567890123/us-east-1", "234567890123/us-west-2"],
                },
            ],
        ),
    ] = {}
    """Explicitly enable/disable the deployment for a specific deploy environment,
    AWS Account ID, and AWS Region combination.
    Can also be set as a static boolean value. (supports lookups)

    """

    modules: Annotated[
        list[RunwayModuleDefinitionModel],
        Field(description="An array of modules to process as part of a deployment."),
    ]
    """An array of modules to process as part of a deployment."""

    module_options: Annotated[
        dict[str, Any] | str,
        Field(
            description="Options that are passed directly to the modules within this deployment. "
            "(supports lookups)",
            examples=[
                "${var sampleapp.options.${env DEPLOY_ENVIRONMENT}}",
                {"some_option": "value"},
            ],
        ),
    ] = {}
    """Options that are passed directly to the modules within this deployment. (supports lookups)"""

    name: Annotated[
        str,
        Field(
            description="The name of the deployment to be displayed in logs and the "
            "interactive selection menu.",
        ),
    ] = "unnamed_deployment"
    """The name of the deployment to be displayed in logs and the interactive selection menu."""

    parallel_regions: Annotated[
        list[str] | str,
        Field(
            description="An array of AWS Regions to process asynchronously. (supports lookups)",
            examples=[
                ["us-east-1", "us-west-2"],
                "${var regions.${dev DEPLOY_ENVIRONMENT}}",
            ],
        ),
    ] = []
    """An array of AWS Regions to process asynchronously. (supports lookups)"""

    parameters: Annotated[
        dict[str, Any] | str,
        Field(
            description="Used to pass variable values to modules in place of an "
            "environment configuration file. (supports lookups)",
            examples=[
                {"namespace": "example-${env DEPLOY_ENVIRONMENT}"},
                "${var sampleapp.parameters.${env DEPLOY_ENVIRONMENT}}",
            ],
        ),
    ] = {}
    """Used to pass variable values to modules in place of an environment configuration file. (supports lookups)"""

    regions: Annotated[
        list[str] | str,
        Field(
            description="An array of AWS Regions to process this deployment in. (supports lookups)",
            examples=[
                ["us-east-1", "us-west-2"],
                "${var regions.${dev DEPLOY_ENVIRONMENT}}",
                *cast(
                    "dict[str, list[str]]",
                    RunwayDeploymentRegionDefinitionModel.model_config.get("json_schema_extra", {}),
                ).get("examples", []),
            ],
        ),
    ] = []
    """An array of AWS Regions to process this deployment in. (supports lookups)"""

    @model_validator(mode="before")
    @classmethod
    def _convert_simple_module(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Convert simple modules to dicts."""
        modules = values.get("modules", [])
        result: list[dict[str, Any]] = []
        for module in modules:
            if isinstance(module, str):
                result.append({"path": module})
            else:
                result.append(module)
        values["modules"] = result
        return values

    @model_validator(mode="before")
    @classmethod
    def _validate_regions(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Validate & simplify regions."""
        raw_regions: str | list[str] = values.get("regions", [])
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
            regions = RunwayDeploymentRegionDefinitionModel.model_validate(raw_regions)

        if regions and parallel_regions:
            raise ValueError("only one of parallel_regions or regions can be defined")
        if not regions and not parallel_regions:
            raise ValueError("either parallel_regions or regions must be defined")

        if isinstance(regions, RunwayDeploymentRegionDefinitionModel):
            values["regions"] = []
            values["parallel_regions"] = regions.parallel
        return values

    _validate_string_is_lookup = field_validator(
        "env_vars",
        "environments",
        "module_options",
        "parallel_regions",
        "parameters",
        "regions",
        mode="before",
    )(utils.validate_string_is_lookup)


class RunwayVersionField(SpecifierSet):
    """Extends packaging.specifiers.SpecifierSet for use with pydantic."""

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        """Yield one of more validators with will be called to validate the input.

        Each validator will receive, as input, the value returned from the previous validator.

        """
        assert source_type is RunwayVersionField  # noqa: S101
        return core_schema.no_info_before_validator_function(
            cls._convert_value,
            core_schema.any_schema(),
            serialization=core_schema.plain_serializer_function_ser_schema(
                str, info_arg=False, return_schema=core_schema.str_schema()
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, schema: core_schema.JsonSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:  # cov: ignore
        """Mutate the field schema in place.

        This is only called when output JSON schema from a model.

        """
        json_schema = handler(schema)
        json_schema = handler.resolve_ref_schema(json_schema)
        json_schema["type"] = "str"
        return json_schema

    @classmethod
    def _convert_value(cls, v: str | SpecifierSet) -> RunwayVersionField:
        """Convert runway_version string into SpecifierSet with some value handling.

        Args:
            v: The value to be converted/validated.

        Raises:
            ValueError: The provided value is not a valid version specifier set.

        """
        if isinstance(v, (cls, SpecifierSet)):
            return RunwayVersionField(str(v), prereleases=True)
        try:
            return RunwayVersionField(v, prereleases=True)
        except InvalidSpecifier:
            if any(v.startswith(i) for i in ["!", "~", "<", ">", "="]):
                raise ValueError(f"{v} is not a valid version specifier set") from None
            LOGGER.debug(
                "runway_version is not a valid version specifier; trying as an exact version",
                exc_info=True,
            )
            return RunwayVersionField("==" + v, prereleases=True)


class RunwayConfigDefinitionModel(ConfigProperty):
    """Runway configuration definition model."""

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_schema_extra={
            "description": "Configuration file for use with Runway.",
        },
        extra="forbid",
        title="Runway Configuration File",
        validate_default=True,
        validate_assignment=True,
    )

    deployments: Annotated[
        list[RunwayDeploymentDefinitionModel],
        Field(description="Array of Runway deployments definitions."),
    ] = []
    """Array of Runway deployments definitions."""

    future: Annotated[
        RunwayFutureDefinitionModel,
        Field(description="Enable future features before they become default behavior."),
    ] = RunwayFutureDefinitionModel()
    """Enable future features before they become default behavior."""

    ignore_git_branch: Annotated[
        bool,
        Field(
            description="Optionally exclude the git branch name when determining the "
            "current deploy environment.",
        ),
    ] = False
    """Optionally exclude the git branch name when determining the current deploy environment."""

    runway_version: Annotated[
        RunwayVersionField | None,
        Field(
            description="Define the versions of Runway that can be used with this "
            "configuration file.",
            examples=['"<2.0.0"', '"==1.14.0"', '">=1.14.0,<2.0.0"'],
        ),
    ] = None
    """Define the versions of Runway that can be used with this configuration file."""

    tests: Annotated[
        list[RunwayTestDefinitionModel],
        Field(
            description="Array of Runway test definitions that are executed with the 'test' command."
        ),
    ] = []

    variables: Annotated[RunwayVariablesDefinitionModel, Field(description="Runway variables.")] = (
        RunwayVariablesDefinitionModel()
    )
    """Runway variables."""

    @model_validator(mode="before")
    @classmethod
    def _add_deployment_names(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Add names to deployments that are missing them."""
        deployments = values.get("deployments", [])
        for i, deployment in enumerate(deployments):
            if not deployment.get("name"):
                deployment["name"] = f"deployment_{i + 1}"
        values["deployments"] = deployments
        return values

    @field_serializer("runway_version", when_used="json-unless-none")
    def _serialize_runway_version(self, runway_version: RunwayVersionField, _info: Any) -> str:
        """Serialize ``runway_version`` field when dumping to JSON."""
        return str(runway_version)

    @classmethod
    def parse_file(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls: type[Self], path: str | Path
    ) -> Self:
        """Parse a file."""
        return cls.model_validate(
            yaml.safe_load(
                Path(path).read_text(encoding=locale.getpreferredencoding(do_setlocale=False))
            )
        )
