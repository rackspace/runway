"""Runway Module definition model."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from pydantic import ConfigDict, Field, ValidationInfo, field_validator, model_validator

from .. import utils
from ..base import ConfigProperty
from ._type_defs import (
    RunwayEnvironmentsUnresolvedType,
    RunwayEnvVarsUnresolvedType,
    RunwayModuleTypeTypeDef,
)


class RunwayModuleDefinitionModel(ConfigProperty):
    """Defines a directory containing IaC, parameters, and options for the module type."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "description": "Defines a directory containing IaC, "
            "the parameters to pass in during execution, "
            "and any applicable options for the module type.",
        },
        title="Runway Module Definition",
        use_enum_values=True,
        validate_default=True,
        validate_assignment=True,
    )

    class_path: Annotated[
        str | None,
        Field(
            description="Import path to a custom Runway module class. (supports lookups)",
        ),
    ] = None
    """Import path to a custom Runway module class. (supports lookups)"""

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

    name: Annotated[
        str,
        Field(
            description="The name of the module to be displayed in logs and the "
            "interactive selection menu."
        ),
    ] = "undefined"
    """The name of the module to be displayed in logs and the interactive selection menu."""

    options: Annotated[
        dict[str, Any] | str, Field(description="Module type specific options. (supports lookups)")
    ] = {}
    """Module type specific options. (supports lookups)"""

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

    path: Annotated[
        Path | str | None,
        Field(
            description="Directory (relative to the Runway config file) containing IaC. "
            "(supports lookups)",
            examples=["./", "sampleapp-${env DEPLOY_ENVIRONMENT}.cfn", "sampleapp.sls"],
        ),
    ] = None
    """Directory (relative to the Runway config file) containing IaC. (supports lookups)"""

    tags: Annotated[
        list[str],
        Field(
            description="Array of values to categorize the module which can be used "
            "with the CLI to quickly select a group of modules. "
            "This field is only used by the `--tag` CLI option.",
            examples=[["type:network", "app:sampleapp"]],
        ),
    ] = []
    """Array of values to categorize the module which can be used with the CLI to
    quickly select a group of modules.

    This field is only used by the ``--tag`` CLI option.

    """

    type: Annotated[
        RunwayModuleTypeTypeDef | None,
        Field(
            description="Explicitly define the module type. If not provided, this will be inferred."
        ),
    ] = None
    """Explicitly define the module type. If not provided, this will be inferred."""

    # needs to be last
    parallel: Annotated[
        list[RunwayModuleDefinitionModel],
        Field(
            description="Array of module definitions that can be executed asynchronously. "
            "Incompatible with class_path, path, and type.",
            examples=[[{"path": "sampleapp-01.cfn"}, {"path": "sampleapp-02.cfn"}]],
        ),
    ] = []
    """List of module definitions that can be executed asynchronously.
    Incompatible with class_path, path, and type.

    """

    @model_validator(mode="before")
    @classmethod
    def _validate_name(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Validate module name."""
        if "name" in values:
            return values
        if "parallel" in values:
            values["name"] = "parallel_parent"
            return values
        if "path" in values and values:
            values["name"] = Path(values["path"]).resolve().name
            return values
        return values

    @model_validator(mode="before")
    @classmethod
    def _validate_path(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Validate path and sets a default value if needed."""
        if not values.get("path") and not values.get("parallel"):
            values["path"] = Path.cwd()
        return values

    @field_validator("parallel", mode="before")
    @classmethod
    def _validate_parallel(
        cls, v: list[dict[str, Any] | str], info: ValidationInfo
    ) -> list[dict[str, Any]]:
        """Validate parallel."""
        if v and info.data.get("path"):
            raise ValueError("only one of parallel or path can be defined")
        result: list[dict[str, Any]] = []
        for mod in v:
            if isinstance(mod, str):
                result.append({"path": mod})
            else:
                result.append(mod)
        return result

    # TODO(kyle): add regex to schema
    _validate_string_is_lookup = field_validator(
        "env_vars", "environments", "options", "parameters", mode="before"
    )(utils.validate_string_is_lookup)
