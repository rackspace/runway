"""CFNgin config models."""
# pylint: disable=no-self-argument,no-self-use
from __future__ import annotations

import copy
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, TypeVar, Union, cast

import yaml
from pydantic import Extra, Field, Protocol, root_validator, validator
from typing_extensions import Literal

from .. import utils
from ..base import ConfigProperty
from ._package_sources import (
    CfnginPackageSourcesDefinitionModel,
    GitCfnginPackageSourceDefinitionModel,
    LocalCfnginPackageSourceDefinitionModel,
    S3CfnginPackageSourceDefinitionModel,
)

if TYPE_CHECKING:
    from pydantic import BaseModel

    Model = TypeVar("Model", bound=BaseModel)

__all__ = [
    "CfnginConfigDefinitionModel",
    "CfnginHookDefinitionModel",
    "CfnginPackageSourcesDefinitionModel",
    "CfnginStackDefinitionModel",
    "GitCfnginPackageSourceDefinitionModel",
    "LocalCfnginPackageSourceDefinitionModel",
    "S3CfnginPackageSourceDefinitionModel",
]


class CfnginHookDefinitionModel(ConfigProperty):
    """Model for a CFNgin hook definition."""

    args: Dict[str, Any] = Field(
        {},
        title="Arguments",
        description="Arguments that will be passed to the hook. (supports lookups)",
    )
    data_key: Optional[str] = Field(
        None, description="Key to use when storing the returned result of the hook."
    )
    enabled: bool = Field(True, description="Whether the hook will be run.")
    path: str = Field(..., description="Python importable path to the hook.")
    required: bool = Field(
        True,
        description="Whether to continue execution if the hook results in an error.",
    )

    class Config(ConfigProperty.Config):
        """Model configuration."""

        extra = Extra.forbid
        schema_extra = {
            "description": "Python classes or functions run before or after "
            "deploy/destroy actions."
        }
        title = "CFNgin Hook Definition"


class CfnginStackDefinitionModel(ConfigProperty):
    """Model for a CFNgin stack definition."""

    class_path: Optional[str] = Field(
        None,
        title="Blueprint Class Path",
        description="Python importable path to a blueprint class.",
    )
    description: Optional[str] = Field(
        None,
        title="Stack Description",
        description="A description that will be applied to the stack in CloudFormation.",
    )
    enabled: bool = Field(True, description="Whether the stack will be deployed.")
    in_progress_behavior: Optional[Literal["wait"]] = Field(
        None,
        title="Stack In Progress Behavior",
        description="The action to take when a stack's status is "
        "CREATE_IN_PROGRESS or UPDATE_IN_PROGRESS when trying to update it.",
    )
    locked: bool = Field(False, description="Whether to limit updating of the stack.")
    name: str = Field(..., title="Stack Name", description="Name of the stack.")
    protected: bool = Field(
        False,
        description="Whether to force all updates to the stack to be performed interactively.",
    )
    required_by: List[str] = Field(
        [], description="Array of stacks (by name) that require this stack."
    )
    requires: List[str] = Field(
        [], description="Array of stacks (by name) that this stack requires."
    )
    stack_name: Optional[str] = Field(
        None,
        title="Explicit Stack Name",
        description="Explicit name of the stack (namespace will still be prepended).",
    )
    stack_policy_path: Optional[Path] = Field(
        None,
        description="Path to a stack policy document that will be applied to the "
        "CloudFormation stack.",
    )
    tags: Dict[str, Any] = Field(
        {}, description="Tags that will be applied to the CloudFormation stack."
    )
    template_path: Optional[Path] = Field(
        None, description="Path to a JSON or YAML formatted CloudFormation Template."
    )
    termination_protection: bool = Field(
        False,
        description="Set the value of termination protection on the CloudFormation stack.",
    )
    timeout: Optional[int] = Field(
        None,
        description="The amount of time (in minutes) that can pass before the "
        "Stack status becomes CREATE_FAILED.",
    )
    variables: Dict[str, Any] = Field(
        {},
        description="Parameter values that will be passed to the "
        "Blueprint/CloudFormation stack. (supports lookups)",
    )

    class Config(ConfigProperty.Config):
        """Model configuration options."""

        extra = Extra.forbid
        title = "CFNgin Stack Definition"

        @staticmethod
        def schema_extra(schema: Dict[str, Any]) -> None:  # type: ignore
            """Processess the schema after it has been generated.

            Schema is modified in place. Return value is ignored.

            https://pydantic-docs.helpmanual.io/usage/schema/#schema-customization

            """
            schema[
                "description"
            ] = "Define CloudFormation stacks using a Blueprint or Template."
            # prevents a false error when defining stacks as a dict
            schema.get("required", ["name"]).remove("name")

            # fields that can be bool or lookup
            for prop in ["enabled", "locked", "protected", "termination_protection"]:
                schema["properties"][prop].pop("type")
                schema["properties"][prop]["anyOf"] = [
                    {"type": "boolean"},
                    {"type": "string", "pattern": utils.CFNGIN_LOOKUP_STRING_REGEX},
                ]

    _resolve_path_fields = validator(
        "stack_policy_path", "template_path", allow_reuse=True
    )(utils.resolve_path_field)

    @root_validator(pre=True)
    def _validate_class_and_template(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate class_path and template_path are not both provided."""
        if values.get("class_path") and values.get("template_path"):
            raise ValueError("only one of class_path or template_path can be defined")
        return values

    @root_validator(pre=True)
    def _validate_class_or_template(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure that either class_path or template_path is defined."""
        # if the stack is disabled or locked, it is ok that these are missing
        required = values.get("enabled", True) and not values.get("locked", False)
        if (
            not values.get("class_path")
            and not values.get("template_path")
            and required
        ):
            raise ValueError("either class_path or template_path must be defined")
        return values


class CfnginConfigDefinitionModel(ConfigProperty):
    """Model for a CFNgin config definition."""

    cfngin_bucket: Optional[str] = Field(
        None,
        title="CFNgin Bucket",
        description="Name of an AWS S3 bucket to use for caching CloudFormation templates. "
        "Set as an empty string to disable caching.",
    )
    cfngin_bucket_region: Optional[str] = Field(
        None,
        title="CFNgin Bucket Region",
        description="AWS Region where the CFNgin Bucket is located. "
        "If not provided, the current region is used.",
    )
    cfngin_cache_dir: Path = Field(
        Path.cwd() / ".runway" / "cache",
        title="CFNgin Cache Directory",
        description="Path to a local directory that CFNgin will use for local caching.",
    )
    log_formats: Dict[str, str] = Field(  # TODO create model
        {}, description="Customize log message formatting by log level."
    )
    lookups: Dict[str, str] = Field(
        {},
        description="Mapping of custom lookup names to a python importable path "
        "for the class that will be used to resolve the lookups.",
    )
    mappings: Dict[str, Dict[str, Dict[str, Any]]] = Field(
        {}, description="Mappings that will be appended to all stack templates."
    )
    namespace: str = Field(
        ...,
        description="The namespace used to prefix stack names to create separation "
        "within an AWS account.",
    )
    namespace_delimiter: str = Field(
        "-",
        description="Character used to separate the namespace and stack name "
        "when the namespace is prepended.",
    )
    package_sources: CfnginPackageSourcesDefinitionModel = Field(
        CfnginPackageSourcesDefinitionModel(),
        description=CfnginPackageSourcesDefinitionModel.Config.schema_extra[
            "description"
        ],
    )
    persistent_graph_key: Optional[str] = Field(
        None,
        description="Key for an AWS S3 object used to track a graph of stacks "
        "between executions.",
    )
    post_deploy: Union[
        List[CfnginHookDefinitionModel],  # final type after parsing
        Dict[str, CfnginHookDefinitionModel],  # recommended when writing config
    ] = Field([], title="Post Deploy Hooks")
    post_destroy: Union[
        List[CfnginHookDefinitionModel],  # final type after parsing
        Dict[str, CfnginHookDefinitionModel],  # recommended when writing config
    ] = Field([], title="Pre Destroy Hooks")
    pre_deploy: Union[
        List[CfnginHookDefinitionModel],  # final type after parsing
        Dict[str, CfnginHookDefinitionModel],  # recommended when writing config
    ] = Field([], title="Pre Deploy Hooks")
    pre_destroy: Union[
        List[CfnginHookDefinitionModel],  # final type after parsing
        Dict[str, CfnginHookDefinitionModel],  # recommended when writing config
    ] = Field([], title="Pre Destroy Hooks")
    service_role: Optional[str] = Field(
        None,
        title="Service Role ARN",
        description="Specify an IAM Role for CloudFormation to use.",
    )
    stacks: Union[
        List[CfnginStackDefinitionModel],  # final type after parsing
        Dict[str, CfnginStackDefinitionModel],  # recommended when writing config
    ] = Field(
        [], description="Define CloudFormation stacks using a Blueprint or Template."
    )
    sys_path: Optional[Path] = Field(
        None,
        title="sys.path",
        description="Path to append to $PATH. This is also the root of relative paths.",
    )
    tags: Optional[Dict[str, str]] = Field(
        None,  # None is significant here
        description="Tags to try to apply to all resources created from this configuration file.",
    )
    template_indent: int = Field(
        4,
        description="Number of spaces per indentation level to use when "
        "rendering/outputting CloudFormation templates.",
    )

    class Config(ConfigProperty.Config):
        """Model configuration."""

        schema_extra = {"description": "Configuration file for Runway's CFNgin."}
        title = "CFNgin Config File"

    _resolve_path_fields = validator("cfngin_cache_dir", "sys_path", allow_reuse=True)(
        utils.resolve_path_field
    )

    @validator("post_deploy", "post_destroy", "pre_deploy", "pre_destroy", pre=True)
    def _convert_hook_definitions(
        cls, v: Union[Dict[str, Any], List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Convert hooks defined as a dict to a list."""
        if isinstance(v, list):
            return v
        return list(v.values())

    @validator("stacks", pre=True)
    def _convert_stack_definitions(
        cls, v: Union[Dict[str, Any], List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Convert stacks defined as a dict to a list."""
        if isinstance(v, list):
            return v
        result: List[Dict[str, Any]] = []
        for name, stack in copy.deepcopy(v).items():
            stack["name"] = name
            result.append(stack)
        return result

    @validator("stacks")
    def _validate_unique_stack_names(
        cls, stacks: List[CfnginStackDefinitionModel]
    ) -> List[CfnginStackDefinitionModel]:
        """Validate that each stack has a unique name."""
        stack_names = [stack.name for stack in stacks]
        if len(set(stack_names)) != len(stack_names):
            for i, name in enumerate(stack_names):
                if stack_names.count(name) != 1:
                    raise ValueError(f"Duplicate stack {name} found at index {i}")
        return stacks

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
