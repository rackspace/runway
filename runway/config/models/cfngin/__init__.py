"""CFNgin config models."""
# pylint: disable=no-self-argument,no-self-use
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import Extra, root_validator, validator

from .. import utils
from ..base import ConfigProperty
from ._package_sources import (
    CfnginPackageSourcesDefinitionModel,
    GitCfnginPackageSourceDefinitionModel,
    LocalCfnginPackageSourceDefinitionModel,
    S3CfnginPackageSourceDefinitionModel,
)

__all__ = [
    "CfnginConfigDefinitionModel",
    "CfnginHookDefinitionModel",
    "CfnginPackageSourcesDefinitionModel",
    "CfnginStackDefinitionModel",
    "CfnginTargetDefinitionModel",
    "GitCfnginPackageSourceDefinitionModel",
    "LocalCfnginPackageSourceDefinitionModel",
    "S3CfnginPackageSourceDefinitionModel",
]


class CfnginHookDefinitionModel(ConfigProperty):
    """Model for a CFNgin hook definition."""

    args: Dict[str, Any] = {}
    data_key: Optional[str] = None
    enabled: bool = True
    path: str
    required: bool = True

    class Config:  # pylint: disable=too-few-public-methods
        """Model configuration."""

        extra = Extra.forbid


class CfnginStackDefinitionModel(ConfigProperty):
    """Model for a CFNgin stack definition."""

    class_path: Optional[str] = None
    description: Optional[str] = None
    enabled: bool = True
    in_progress_behavior: Optional[str] = None  # TODO use enum
    locked: bool = False
    name: str
    profile: Optional[str]  # TODO remove
    protected: bool = False
    region: Optional[str] = None  # TODO remove
    required_by: List[str] = []
    requires: List[str] = []
    stack_name: Optional[str] = None
    stack_policy_path: Optional[Path] = None  # TODO try Path
    tags: Dict[str, Any] = {}
    template_path: Optional[Path] = None  # TODO try Path
    termination_protection: bool = False
    variables: Dict[str, Any] = {}

    class Config:  # pylint: disable=too-few-public-methods
        """Model configuration options."""

        extra = Extra.forbid

    _resolve_path_fields = validator(
        "stack_policy_path", "template_path", allow_reuse=True
    )(utils.resolve_path_field)

    @root_validator(pre=True)
    def _validate_class_and_template(
        cls, values: Dict[str, Any]  # noqa: N805
    ) -> Dict[str, Any]:
        """Validate class_path and template_path are not both provided."""
        if values.get("class_path") and values.get("template_path"):
            raise ValueError("only one of class_path or template_path can be defined")
        return values

    @root_validator(pre=True)
    def _validate_class_or_template(
        cls, values: Dict[str, Any]  # noqa: N805
    ) -> Dict[str, Any]:
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


class CfnginTargetDefinitionModel(ConfigProperty):
    """Model for a CFNgin target definition."""

    name: str
    required_by: List[str] = []
    requires: List[str] = []

    class Config:  # pylint: disable=too-few-public-methods
        """Model configuration."""

        extra = Extra.forbid


class CfnginConfigDefinitionModel(ConfigProperty):
    """Model for a CFNgin config definition."""

    cfngin_bucket: Optional[str] = None
    cfngin_bucket_region: Optional[str] = None
    cfngin_cache_dir: Path = Path.cwd() / ".runway" / "cache"
    log_formats: Dict[str, str] = {}  # TODO create model
    lookups: Dict[str, str] = {}  # TODO create model
    mappings: Dict[str, Dict[str, Dict[str, Any]]] = {}  # TODO create model
    namespace: str
    namespace_delimiter: str = "-"
    package_sources: CfnginPackageSourcesDefinitionModel = CfnginPackageSourcesDefinitionModel()
    persistent_graph_key: Optional[str] = None
    post_build: List[CfnginHookDefinitionModel] = []
    post_destroy: List[CfnginHookDefinitionModel] = []
    pre_build: List[CfnginHookDefinitionModel] = []
    pre_destroy: List[CfnginHookDefinitionModel] = []
    service_role: Optional[str] = None
    stacks: List[CfnginStackDefinitionModel] = []
    sys_path: Optional[Path] = None
    tags: Optional[Dict[str, str]] = None  # None is significant here
    targets: List[CfnginTargetDefinitionModel] = []
    template_indent: int = 4

    _resolve_path_fields = validator("cfngin_cache_dir", "sys_path", allow_reuse=True)(
        utils.resolve_path_field
    )

    @validator("stacks")
    def _validate_unique_stack_names(
        cls, stacks: List[CfnginStackDefinitionModel]  # noqa: N805
    ) -> List[CfnginStackDefinitionModel]:
        """Validate that each stack has a unique name."""
        stack_names = [stack.name for stack in stacks]
        if len(set(stack_names)) != len(stack_names):
            for i, name in enumerate(stack_names):
                if stack_names.count(name) != 1:
                    raise ValueError(f"Duplicate stack {name} found at index {i}")
        return stacks

    @classmethod
    def parse_file(cls, path: Path) -> CfnginConfigDefinitionModel:
        """Parse a file."""
        return cls.parse_raw(path.read_text())

    @classmethod
    def parse_raw(cls, data: str) -> CfnginConfigDefinitionModel:
        """Parse raw data."""
        return cls.parse_obj(yaml.safe_load(data))
