"""Runway config models."""
# pylint: disable=no-self-argument,no-self-use
from __future__ import annotations

import logging
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generator,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
)

import yaml
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from pydantic import Extra, Field, Protocol, root_validator, validator
from typing_extensions import Literal

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

if TYPE_CHECKING:
    from pydantic import BaseModel

    Model = TypeVar("Model", bound=BaseModel)

LOGGER = logging.getLogger(__name__)

RunwayEnvironmentsType = Dict[str, Union[bool, List[str], str]]
RunwayEnvironmentsUnresolvedType = Union[Dict[str, Union[bool, List[str], str]], str]
RunwayEnvVarsType = Dict[str, Union[List[str], str]]
RunwayEnvVarsUnresolvedType = Union[RunwayEnvVarsType, str]
RunwayModuleTypeTypeDef = Literal[
    "cdk", "cloudformation", "kubernetes", "serverless", "static", "terraform"
]

__all__ = [
    "CfnLintRunwayTestArgs",
    "CfnLintRunwayTestDefinitionModel",
    "RUNWAY_LOOKUP_STRING_ERROR",
    "RUNWAY_LOOKUP_STRING_REGEX",
    "RunwayAssumeRoleDefinitionModel",
    "RunwayConfigDefinitionModel",
    "RunwayDeploymentDefinitionModel",
    "RunwayDeploymentRegionDefinitionModel",
    "RunwayEnvironmentsType",
    "RunwayEnvironmentsUnresolvedType",
    "RunwayEnvVarsType",
    "RunwayEnvVarsUnresolvedType",
    "RunwayFutureDefinitionModel",
    "RunwayModuleDefinitionModel",
    "RunwayModuleTypeTypeDef",
    "RunwayTestDefinitionModel",
    "RunwayVariablesDefinitionModel",
    "RunwayVersionField",
    "ScriptRunwayTestArgs",
    "ScriptRunwayTestDefinitionModel",
    "ValidRunwayTestTypeValues",
    "YamlLintRunwayTestDefinitionModel",
]


class RunwayAssumeRoleDefinitionModel(ConfigProperty):
    """Model for a Runway assume role definition."""

    arn: Optional[str] = Field(
        None,
        title="IAM Role ARN",
        description="The ARN of the AWS IAM role to be assumed. (supports lookups)",
    )
    duration: Union[int, str] = Field(
        3600,
        description="The duration, in seconds, of the role session. (supports lookups)",
        ge=900,  # applies to int json schema only
        le=43_200,  # applies to int json schema only
        regex=RUNWAY_LOOKUP_STRING_REGEX,  # applies to str json schema only
    )
    post_deploy_env_revert: bool = Field(
        False,
        title="Post Deployment Environment Revert",
        description="Revert the credentials stored in environment variables to "
        "what they were prior to execution after the deployment finished processing. "
        "(supports lookups)",
    )
    session_name: str = Field(
        "runway",
        description="An identifier for the assumed role session. (supports lookups)",
    )

    class Config(ConfigProperty.Config):
        """Model configuration."""

        extra = Extra.forbid
        schema_extra: Dict[str, Any] = {
            "description": "Used to defined a role to assume while Runway is "
            "processing each module.",
            "examples": [
                {"arn": "arn:aws:iam::123456789012:role/name"},
                {
                    "arn": "${var role_arn.${env DEPLOY_ENVIRONMENT}}",
                    "duration": 9001,
                    "post_deploy_env_revert": True,
                    "session_name": "runway-example",
                },
            ],
        }
        title = "Runway Deployment.assume_role Definition"

    @validator("arn")
    def _convert_arn_null_value(cls, v: Optional[str]) -> Optional[str]:
        """Convert a "nul" string into type(None)."""
        null_strings = ["null", "none", "undefined"]
        return None if isinstance(v, str) and v.lower() in null_strings else v

    @validator("duration", pre=True)
    def _validate_duration(cls, v: Union[int, str]) -> Union[int, str]:
        """Validate duration is within the range allowed by AWS."""
        if isinstance(v, str):
            return v
        if v < 900:
            raise ValueError("duration must be greater than or equal to 900")
        if v > 43_200:
            raise ValueError("duration must be less than or equal to 43,200")
        return v

    _validate_string_is_lookup = validator("duration", allow_reuse=True, pre=True)(
        utils.validate_string_is_lookup
    )


class RunwayDeploymentRegionDefinitionModel(ConfigProperty):
    """Model for a Runway deployment region definition."""

    parallel: Union[List[str], str] = Field(
        ...,
        title="Parallel Regions",
        description="An array of AWS Regions to process asynchronously. (supports lookups)",
    )

    class Config(ConfigProperty.Config):
        """Model configuration."""

        extra = Extra.forbid
        schema_extra: Dict[str, Any] = {
            "description": "Only supports 'parallel' field.",
            "examples": [
                {"parallel": ["us-east-1", "us-east-2"]},
                {"parallel": "${var regions.${env DEPLOY_ENVIRONMENT}}"},
            ],
        }
        title = "Runway Deployment.regions Definition"

    _validate_string_is_lookup = validator("parallel", allow_reuse=True, pre=True)(
        utils.validate_string_is_lookup
    )


class RunwayDeploymentDefinitionModel(ConfigProperty):
    """Model for a Runway deployment definition."""

    account_alias: Optional[str] = Field(
        None,
        description="Used to verify the currently assumed role or credentials. "
        "(supports lookups)",
        examples=["example-alias", "${var alias.${env DEPLOY_ENVIRONMENT}}"],
    )
    account_id: Optional[str] = Field(
        None,
        description="Used to verify the currently assumed role or credentials. "
        "(supports lookups)",
        examples=["123456789012", "${var id.${env DEPLOY_ENVIRONMENT}}"],
    )
    assume_role: Union[str, RunwayAssumeRoleDefinitionModel] = Field(
        {},
        description="Assume a role when processing the deployment. (supports lookups)",
        examples=["arn:aws:iam::123456789012:role/name"]
        + cast(
            List[Any], RunwayAssumeRoleDefinitionModel.Config.schema_extra["examples"]
        ),
    )
    env_vars: RunwayEnvVarsUnresolvedType = Field(
        {},
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
    )
    environments: RunwayEnvironmentsUnresolvedType = Field(
        {},
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
    )
    modules: List[RunwayModuleDefinitionModel] = Field(
        ..., description="An array of modules to process as part of a deployment."
    )
    module_options: Union[Dict[str, Any], str] = Field(
        {},
        description="Options that are passed directly to the modules within this deployment. "
        "(supports lookups)",
        examples=[
            "${var sampleapp.options.${env DEPLOY_ENVIRONMENT}}",
            {"some_option": "value"},
        ],
    )
    name: str = Field(
        "unnamed_deployment",
        description="The name of the deployment to be displayed in logs and the "
        "interactive selection menu.",
    )
    parallel_regions: Union[List[str], str] = Field(
        [],
        description="An array of AWS Regions to process asynchronously. (supports lookups)",
        examples=[
            ["us-east-1", "us-west-2"],
            "${var regions.${dev DEPLOY_ENVIRONMENT}}",
        ],
    )
    parameters: Union[Dict[str, Any], str] = Field(
        {},
        description="Used to pass variable values to modules in place of an "
        "environment configuration file. (supports lookups)",
        examples=[
            {"namespace": "example-${env DEPLOY_ENVIRONMENT}"},
            "${var sampleapp.parameters.${env DEPLOY_ENVIRONMENT}}",
        ],
    )
    regions: Union[List[str], str] = Field(
        [],
        description="An array of AWS Regions to process this deployment in. (supports lookups)",
        examples=[
            ["us-east-1", "us-west-2"],
            "${var regions.${dev DEPLOY_ENVIRONMENT}}",
        ]
        + RunwayDeploymentRegionDefinitionModel.Config.schema_extra["examples"],
    )

    class Config(ConfigProperty.Config):
        """Model configuration."""

        extra = Extra.forbid
        title = "Runway Deployment Definition"

        @staticmethod
        def schema_extra(schema: Dict[str, Any]) -> None:  # type: ignore
            """Processess the schema after it has been generated.

            Schema is modified in place. Return value is ignored.

            https://pydantic-docs.helpmanual.io/usage/schema/#schema-customization

            """
            schema[
                "description"
            ] = "A collection of modules, regions, and other configurations to deploy."
            # modify schema to allow simple string or mapping definition for a module
            module_ref = schema["properties"]["modules"]["items"].pop("$ref")
            schema["properties"]["modules"]["items"]["anyOf"] = [
                {"$ref": module_ref},
                {"type": "string"},
            ]

    @root_validator(pre=True)
    def _convert_simple_module(cls, values: Dict[str, Any]) -> Dict[str, Any]:
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
    def _validate_regions(cls, values: Dict[str, Any]) -> Dict[str, Any]:
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

    class Config(ConfigProperty.Config):
        """Model configuration."""

        extra = Extra.forbid
        schema_extra = {
            "description": "Enable features/behaviors that will be become standard "
            "ahead of their official release."
        }
        title = "Runway Future Definition"


class RunwayModuleDefinitionModel(ConfigProperty):
    """Model for a Runway module definition."""

    class_path: Optional[str] = Field(
        None,
        description="Import path to a custom Runway module class. (supports lookups)",
    )
    env_vars: RunwayEnvVarsUnresolvedType = Field(
        {},
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
    )
    environments: RunwayEnvironmentsUnresolvedType = Field(
        {},
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
    )
    name: str = Field(
        "undefined",
        description="The name of the module to be displayed in logs and the "
        "interactive selection menu.",
    )
    options: Union[Dict[str, Any], str] = Field(
        {}, description="Module type specific options. (supports lookups)"
    )
    parameters: Union[Dict[str, Any], str] = Field(
        {},
        description="Used to pass variable values to modules in place of an "
        "environment configuration file. (supports lookups)",
        examples=[
            {"namespace": "example-${env DEPLOY_ENVIRONMENT}"},
            "${var sampleapp.parameters.${env DEPLOY_ENVIRONMENT}}",
        ],
    )
    path: Optional[Union[str, Path]] = Field(
        None,
        description="Directory (relative to the Runway config file) containing IaC. "
        "(supports lookups)",
        examples=["./", "sampleapp-${env DEPLOY_ENVIRONMENT}.cfn", "sampleapp.sls"],
    )
    tags: List[str] = Field(
        [],
        description="Array of values to categorize the module which can be used "
        "with the CLI to quickly select a group of modules. "
        "This field is only used by the `--tag` CLI option.",
        examples=[["type:network", "app:sampleapp"]],
    )
    type: Optional[RunwayModuleTypeTypeDef] = None
    # needs to be last
    parallel: List[RunwayModuleDefinitionModel] = Field(
        [],
        description="Array of module definitions that can be executed asynchronously. "
        "Incompatible with class_path, path, and type.",
        examples=[[{"path": "sampleapp-01.cfn"}, {"path": "sampleapp-02.cfn"}]],
    )

    class Config(ConfigProperty.Config):
        """Model configuration."""

        extra = Extra.forbid
        schema_extra = {
            "description": "Defines a directory containing IaC, "
            "the parameters to pass in during execution, "
            "and any applicable options for the module type.",
        }
        title = "Runway Module Definition"
        use_enum_values = True

    @root_validator(pre=True)
    def _validate_name(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate module name."""
        if "name" in values:
            return values
        if "parallel" in values:
            values["name"] = "parallel_parent"
            return values
        if "path" in values:
            values["name"] = Path(values["path"]).resolve().name
            return values
        return values

    @root_validator(pre=True)
    def _validate_path(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate path and sets a default value if needed."""
        if not values.get("path") and not values.get("parallel"):
            values["path"] = Path.cwd()
        return values

    @validator("parallel", pre=True)
    def _validate_parallel(
        cls, v: List[Union[Dict[str, Any], str]], values: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Validate parallel."""
        if v and values.get("path"):
            raise ValueError("only one of parallel or path can be defined")
        result: List[Dict[str, Any]] = []
        for mod in v:
            if isinstance(mod, str):
                result.append({"path": mod})
            else:
                result.append(mod)
        return result

    # TODO add regex to schema
    _validate_string_is_lookup = validator(
        "env_vars", "environments", "options", "parameters", allow_reuse=True, pre=True
    )(utils.validate_string_is_lookup)


# https://pydantic-docs.helpmanual.io/usage/postponed_annotations/#self-referencing-models
RunwayModuleDefinitionModel.update_forward_refs()


class RunwayVariablesDefinitionModel(ConfigProperty):
    """Model for a Runway variable definition."""

    file_path: Optional[Path] = Field(
        None,
        title="Variables File Path",
        description="Explicit path to a variables file that will be loaded and "
        "merged with the variables defined here.",
    )
    sys_path: Path = Field(
        "./",
        description="Directory to use as the root of a relative 'file_path'. "
        "If not provided, the current working directory is used.",
    )

    class Config(ConfigProperty.Config):
        """Model configuration."""

        extra = Extra.allow
        schema_extra = {
            "description": "A variable definitions for the Runway config file. "
            "This is used to resolve the 'var' lookup.",
        }
        title = "Runway Variables Definition"

    _convert_null_values = validator("*", allow_reuse=True)(utils.convert_null_values)


class RunwayVersionField(SpecifierSet):
    """Extends packaging.specifiers.SpecifierSet for use with pydantic."""

    @classmethod
    def __get_validators__(cls) -> Generator[Callable[..., Any], None, None]:
        """Yield one of more validators with will be called to validate the input.

        Each validator will receive, as input, the value returned from the previous validator.

        """
        yield cls._convert_value

    @classmethod
    def __modify_schema__(cls, field_schema: Dict[str, Any]) -> None:
        """Mutate the field schema in place.

        This is only called when output JSON schema from a model.

        """
        field_schema.update(type="string")  # cov: ignore

    @classmethod
    def _convert_value(cls, v: Union[str, SpecifierSet]) -> RunwayVersionField:
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

    deployments: List[RunwayDeploymentDefinitionModel] = Field(
        [], description="Array of Runway deployments definitions."
    )
    future: RunwayFutureDefinitionModel = RunwayFutureDefinitionModel()
    ignore_git_branch: bool = Field(
        False,
        description="Optionally exclude the git branch name when determining the "
        "current deploy environment.",
    )
    runway_version: Optional[RunwayVersionField] = Field(
        ">1.10",
        description="Define the versions of Runway that can be used with this "
        "configuration file.",
        examples=['"<2.0.0"', '"==1.14.0"', '">=1.14.0,<2.0.0"'],
    )
    tests: List[RunwayTestDefinitionModel] = Field(
        [],
        description="Array of Runway test definitions that are executed with the 'test' command.",
    )
    variables: RunwayVariablesDefinitionModel = RunwayVariablesDefinitionModel()

    class Config(ConfigProperty.Config):
        """Model configuration."""

        extra = Extra.forbid
        schema_extra = {
            "description": "Configuration file for use with Runway.",
        }
        title = "Runway Configuration File"
        validate_all = True
        validate_assignment = True

    @root_validator(pre=True)
    def _add_deployment_names(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Add names to deployments that are missing them."""
        deployments = values.get("deployments", [])
        for i, deployment in enumerate(deployments):
            if not deployment.get("name"):
                deployment["name"] = f"deployment_{i + 1}"
        values["deployments"] = deployments
        return values

    @classmethod
    def parse_file(
        cls: Type[Model],
        path: Union[str, Path],
        *,
        content_type: Optional[str] = None,
        encoding: str = "utf8",
        proto: Optional[Protocol] = None,
        allow_pickle: bool = False,
    ) -> Model:
        """Parse a file."""
        return cast(
            "Model",
            cls.parse_raw(
                path.read_text() if isinstance(path, Path) else Path(path).read_text(),
                content_type=content_type,  # type: ignore
                encoding=encoding,
                proto=proto,  # type: ignore
                allow_pickle=allow_pickle,
            ),
        )

    @classmethod
    def parse_raw(
        cls: Type[Model],
        b: Union[bytes, str],
        *,
        content_type: Optional[str] = None,  # pylint: disable=unused-argument
        encoding: str = "utf8",  # pylint: disable=unused-argument
        proto: Optional[Protocol] = None,  # pylint: disable=unused-argument
        allow_pickle: bool = False,  # pylint: disable=unused-argument
    ) -> Model:
        """Parse raw data."""
        return cast("Model", cls.parse_obj(yaml.safe_load(b)))


# https://pydantic-docs.helpmanual.io/usage/postponed_annotations/#self-referencing-models
RunwayDeploymentDefinitionModel.update_forward_refs()
