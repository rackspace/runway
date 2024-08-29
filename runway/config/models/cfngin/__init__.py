"""CFNgin config models."""

from __future__ import annotations

import copy
import locale
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, cast

import yaml
from pydantic import ConfigDict, Field, field_validator, model_validator
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
    from pydantic.config import JsonDict
    from typing_extensions import Self

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

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "description": "Python classes or functions run before or after deploy/destroy actions."
        },
        title="CFNgin Hook Definition",
        validate_default=True,
        validate_assignment=True,
    )

    args: Annotated[
        dict[str, Any],
        Field(
            title="Arguments",
            description="Arguments that will be passed to the hook. (supports lookups)",
        ),
    ] = {}
    data_key: Annotated[
        str | None, Field(description="Key to use when storing the returned result of the hook.")
    ] = None
    enabled: Annotated[bool, Field(description="Whether the hook will be run.")] = True
    path: Annotated[str, Field(description="Python importable path to the hook.")]
    required: Annotated[
        bool, Field(description="Whether to continue execution if the hook results in an error.")
    ] = True


@staticmethod
def _stack_json_schema_extra(schema: JsonDict) -> None:
    """Process the schema after it has been generated.

    Schema is modified in place. Return value is ignored.

    https://pydantic-docs.helpmanual.io/usage/schema/#schema-customization

    """
    schema["description"] = "Define CloudFormation stacks using a Blueprint or Template."

    # prevents a false error when defining stacks as a dict
    if "required" in schema and isinstance(schema["required"], list):
        schema["required"].remove("name")

    # fields that can be bool or lookup
    if "properties" in schema and isinstance(schema["properties"], dict):
        properties = schema["properties"]
        for field_name in ["enabled", "locked", "protected", "termination_protection"]:
            if field_name in properties and isinstance(properties[field_name], dict):
                field_schema = cast("JsonDict", properties[field_name])
                field_schema.pop("type")
                field_schema["anyOf"] = [
                    {"type": "boolean"},
                    {"type": "string", "pattern": utils.CFNGIN_LOOKUP_STRING_REGEX},
                ]


class CfnginStackDefinitionModel(ConfigProperty):
    """Model for a CFNgin stack definition."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra=_stack_json_schema_extra,
        title="CFNgin Stack Definition",
        validate_default=True,
        validate_assignment=True,
    )

    class_path: Annotated[
        str | None,
        Field(
            title="Blueprint Class Path", description="Python importable path to a blueprint class."
        ),
    ] = None
    """Python importable path to a blueprint class."""

    description: Annotated[
        str | None,
        Field(
            title="Stack Description",
            description="A description that will be applied to the stack in CloudFormation.",
        ),
    ] = None
    """A description that will be applied to the stack in CloudFormation."""

    enabled: Annotated[bool, Field(description="Whether the stack will be deployed.")] = True
    """Whether the stack will be deployed."""

    in_progress_behavior: Annotated[
        Literal["wait"] | None,
        Field(
            title="Stack In Progress Behavior",
            description="The action to take when a stack's status is "
            "CREATE_IN_PROGRESS or UPDATE_IN_PROGRESS when trying to update it.",
        ),
    ] = None
    """The action to take when a Stack's status is ``CREATE_IN_PROGRESS`` or
    ``UPDATE_IN_PROGRESS`` when trying to update it.

    """

    locked: Annotated[bool, Field(description="Whether to limit updating of the stack.")] = False
    """Whether to limit updating of the stack."""

    name: Annotated[str, Field(title="Stack Name", description="Name of the stack.")]
    """Name of the stack."""

    protected: Annotated[
        bool,
        Field(
            description="Whether to force all updates to the stack to be performed interactively."
        ),
    ] = False
    """Whether to force all updates to the stack to be performed interactively."""

    required_by: Annotated[
        list[str], Field(description="Array of stacks (by name) that require this stack.")
    ] = []
    """Array of stacks (by name) that require this stack."""

    requires: Annotated[
        list[str], Field(description="Array of stacks (by name) that this stack requires.")
    ] = []
    """Array of stacks (by name) that this stack requires."""

    stack_name: Annotated[
        str | None,
        Field(
            title="Explicit Stack Name",
            description="Explicit name of the stack (namespace will still be prepended).",
        ),
    ] = None
    """Explicit name of the stack (namespace will still be prepended)."""

    stack_policy_path: Annotated[
        Path | None,
        Field(
            description="Path to a stack policy document that will be applied to the CloudFormation stack."
        ),
    ] = None
    """Path to a stack policy document that will be applied to the CloudFormation stack."""

    tags: Annotated[
        dict[str, Any], Field(description="Tags that will be applied to the CloudFormation stack.")
    ] = {}
    """Tags that will be applied to the CloudFormation stack."""

    template_path: Annotated[
        Path | None, Field(description="Path to a JSON or YAML formatted CloudFormation Template.")
    ] = None
    """Path to a JSON or YAML formatted CloudFormation Template."""

    termination_protection: Annotated[
        bool,
        Field(description="Set the value of termination protection on the CloudFormation stack."),
    ] = False
    """Set the value of termination protection on the CloudFormation stack."""

    timeout: Annotated[
        int | None,
        Field(
            description="The amount of time (in minutes) that can pass before the Stack status becomes CREATE_FAILED."
        ),
    ] = None
    """The amount of time (in minutes) that can pass before the Stack status becomes CREATE_FAILED."""

    variables: Annotated[
        dict[str, Any],
        Field(
            description="Parameter values that will be passed to the Blueprint/CloudFormation stack. (supports lookups)"
        ),
    ] = {}
    """Parameter values that will be passed to the Blueprint/CloudFormation stack. (supports lookups)"""

    _resolve_path_fields = field_validator("stack_policy_path", "template_path")(
        utils.resolve_path_field
    )

    @model_validator(mode="before")
    @classmethod
    def _validate_class_and_template(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Validate class_path and template_path are not both provided."""
        if values.get("class_path") and values.get("template_path"):
            raise ValueError("only one of class_path or template_path can be defined")
        return values

    @model_validator(mode="before")
    @classmethod
    def _validate_class_or_template(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Ensure that either class_path or template_path is defined."""
        # if the Stack is disabled or locked, it is ok that these are missing
        required = values.get("enabled", True) and not values.get("locked", False)
        if not values.get("class_path") and not values.get("template_path") and required:
            raise ValueError("either class_path or template_path must be defined")
        return values


class CfnginConfigDefinitionModel(ConfigProperty):
    """Model for a CFNgin config definition."""

    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={"description": "Configuration file for Runway's CFNgin."},
        title="CFNgin Config File",
        validate_default=True,
        validate_assignment=True,
    )

    cfngin_bucket: Annotated[
        str | None,
        Field(
            title="CFNgin Bucket",
            description="Name of an AWS S3 bucket to use for caching CloudFormation templates. "
            "Set as an empty string to disable caching.",
        ),
    ] = None
    cfngin_bucket_region: Annotated[
        str | None,
        Field(
            title="CFNgin Bucket Region",
            description="AWS Region where the CFNgin Bucket is located. "
            "If not provided, the current region is used.",
        ),
    ] = None
    cfngin_cache_dir: Annotated[
        Path | None,
        Field(
            title="CFNgin Cache Directory",
            description="Path to a local directory that CFNgin will use for local caching.",
        ),
    ] = None
    log_formats: Annotated[  # TODO (kyle): create model
        dict[str, str], Field(description="Customize log message formatting by log level.")
    ] = {}
    lookups: Annotated[
        dict[str, str],
        Field(
            description="Mapping of custom lookup names to a python importable path "
            "for the class that will be used to resolve the lookups.",
        ),
    ] = {}
    mappings: Annotated[
        dict[str, dict[str, dict[str, Any]]],
        Field(description="Mappings that will be appended to all stack templates."),
    ] = {}
    namespace: Annotated[
        str,
        Field(
            description="The namespace used to prefix stack names to create separation "
            "within an AWS account.",
        ),
    ]
    namespace_delimiter: Annotated[
        str,
        Field(
            description="Character used to separate the namespace and stack name "
            "when the namespace is prepended.",
        ),
    ] = "-"
    package_sources: Annotated[
        CfnginPackageSourcesDefinitionModel,
        Field(
            description="Map of additional package sources to include when "
            "processing this configuration file.",
        ),
    ] = CfnginPackageSourcesDefinitionModel()
    persistent_graph_key: Annotated[
        str | None,
        Field(
            description="Key for an AWS S3 object used to track a graph of stacks "
            "between executions.",
        ),
    ] = None
    post_deploy: Annotated[
        list[CfnginHookDefinitionModel] | dict[str, CfnginHookDefinitionModel],
        Field(title="Post Deploy Hooks"),
    ] = []
    post_destroy: Annotated[
        list[CfnginHookDefinitionModel] | dict[str, CfnginHookDefinitionModel],
        Field(title="Pre Destroy Hooks"),
    ] = []
    pre_deploy: Annotated[
        list[CfnginHookDefinitionModel] | dict[str, CfnginHookDefinitionModel],
        Field(title="Pre Deploy Hooks"),
    ] = []
    pre_destroy: Annotated[
        list[CfnginHookDefinitionModel] | dict[str, CfnginHookDefinitionModel],
        Field(title="Pre Destroy Hooks"),
    ] = []
    service_role: Annotated[
        str | None,
        Field(
            title="Service Role ARN",
            description="Specify an IAM Role for CloudFormation to use.",
        ),
    ] = None
    stacks: Annotated[
        list[CfnginStackDefinitionModel] | dict[str, CfnginStackDefinitionModel],
        Field(
            description="Define CloudFormation stacks using a Blueprint or Template.",
        ),
    ] = []
    sys_path: Annotated[
        Path | None,
        Field(
            title="sys.path",
            description="Path to append to $PATH. This is also the root of relative paths.",
        ),
    ] = None
    tags: Annotated[
        dict[str, str] | None,
        Field(
            description="Tags to try to apply to all resources created from this configuration file.",
        ),
    ] = None  # NOTE (kyle): `None` is significant here
    template_indent: Annotated[
        int,
        Field(
            description="Number of spaces per indentation level to use when "
            "rendering/outputting CloudFormation templates.",
        ),
    ] = 4

    _resolve_path_fields = field_validator("cfngin_cache_dir", "sys_path")(utils.resolve_path_field)

    @field_validator("post_deploy", "post_destroy", "pre_deploy", "pre_destroy", mode="before")
    @classmethod
    def _convert_hook_definitions(
        cls, v: dict[str, Any] | list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Convert hooks defined as a dict to a list."""
        if isinstance(v, list):
            return v
        return list(v.values())

    @field_validator("stacks", mode="before")
    @classmethod
    def _convert_stack_definitions(
        cls, v: dict[str, Any] | list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Convert ``stacks`` defined as a dict to a list."""
        if isinstance(v, list):
            return v
        result: list[dict[str, Any]] = []
        for name, stack in copy.deepcopy(v).items():
            stack["name"] = name
            result.append(stack)
        return result

    @field_validator("stacks")
    @classmethod
    def _validate_unique_stack_names(
        cls, stacks: list[CfnginStackDefinitionModel]
    ) -> list[CfnginStackDefinitionModel]:
        """Validate that each Stack has a unique name."""
        stack_names = [stack.name for stack in stacks]
        if len(set(stack_names)) != len(stack_names):
            for i, name in enumerate(stack_names):
                if stack_names.count(name) != 1:
                    raise ValueError(f"Duplicate stack {name} found at index {i}")
        return stacks

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
