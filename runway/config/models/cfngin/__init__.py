"""CFNgin config models."""
# pylint: disable=no-self-argument,no-self-use
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import Extra, root_validator, validator

from ..base import ConfigProperty
from .package_sources import (
    GitPackageSource,
    LocalPackageSource,
    PackageSources,
    S3PackageSource,
)

__all__ = [
    "GitPackageSource",
    "Hook",
    "LocalPackageSource",
    "PackageSources",
    "S3PackageSource",
    "Stack",
    "Target",
]


class Hook(ConfigProperty):
    """Hook module."""

    args: Dict[str, Any] = {}
    data_key: Optional[str]
    enabled: bool = True
    path: str
    required: bool = True


class Stack(ConfigProperty):
    """Stack model."""

    class_path: Optional[str] = None
    description: Optional[str] = None
    enabled: bool = True
    in_progress_behavior: Optional[str] = None
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

    @root_validator(pre=True)
    def _class_and_template(
        cls, values: Dict[str, Any]  # noqa: N805
    ) -> Dict[str, Any]:
        """Validate class_path and template_path are not both provided."""
        if values.get("class_path") and values.get("template_path"):
            raise ValueError("only one of class_path or template_path can be defined")
        return values

    @root_validator(pre=True)
    def _class_or_template(cls, values: Dict[str, Any]) -> Dict[str, Any]:  # noqa: N805
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

    @validator("stack_policy_path", "template_path")
    def _resolve_path_fields(cls, v: Optional[Path]) -> Optional[Path]:  # noqa: N805
        """Resolve sys_path."""
        return v.resolve() if v else v


class Target(ConfigProperty):
    """Target model."""

    name: str
    required_by: List[str] = []
    requires: List[str] = []
