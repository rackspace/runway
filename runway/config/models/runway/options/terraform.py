"""Runway Terraform Module options."""

from __future__ import annotations

from typing import Annotated

from pydantic import ConfigDict, Field, field_validator

from ...base import ConfigProperty


class RunwayTerraformArgsDataModel(ConfigProperty):
    """Model for Runway Terraform Module args option."""

    model_config = ConfigDict(
        extra="forbid",
        title="Runway Terraform Module args option",
        validate_default=True,
        validate_assignment=True,
    )

    apply: list[str] = []
    init: list[str] = []
    plan: list[str] = []


class RunwayTerraformBackendConfigDataModel(ConfigProperty):
    """Model for Runway Terraform Module terraform_backend_config option."""

    model_config = ConfigDict(
        extra="forbid",
        title="Runway Terraform Module terraform_backend_config option",
        validate_default=True,
        validate_assignment=True,
    )

    bucket: str | None = None
    dynamodb_table: str | None = None
    region: str | None = None
    workspace_key_prefix: str | None = None

    def __bool__(self) -> bool:
        """Evaluate the boolean value of the object instance."""
        data = self.model_dump(exclude_none=True)
        return "bucket" in data or "dynamodb_table" in data


class RunwayTerraformModuleOptionsDataModel(ConfigProperty):
    """Model for Runway Terraform Module options."""

    model_config = ConfigDict(
        extra="ignore",
        title="Runway Terraform Module options",
        populate_by_name=True,
        validate_default=True,
        validate_assignment=True,
    )

    args: RunwayTerraformArgsDataModel = RunwayTerraformArgsDataModel()
    backend_config: RunwayTerraformBackendConfigDataModel = Field(
        default=RunwayTerraformBackendConfigDataModel(),
        alias="terraform_backend_config",
    )
    version: Annotated[str | None, Field(alias="terraform_version")] = None
    workspace: Annotated[str | None, Field(alias="terraform_workspace")] = None
    write_auto_tfvars: Annotated[bool, Field(alias="terraform_write_auto_tfvars")] = False

    @field_validator("args", mode="before")
    @classmethod
    def _convert_args(cls, v: list[str] | dict[str, list[str]]) -> dict[str, list[str]]:
        """Convert args from list to dict."""
        if isinstance(v, list):
            return {"apply": v}
        return v
