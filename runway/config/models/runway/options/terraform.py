"""Runway Terraform Module options."""
# pylint: disable=no-self-argument,no-self-use
from __future__ import annotations

from typing import Dict, List, Optional, Union

from pydantic import Extra, Field, validator

from ...base import ConfigProperty


class RunwayTerraformArgsDataModel(ConfigProperty):
    """Modelf for Runway Terraform Module args option."""

    apply: List[str] = []
    init: List[str] = []
    plan: List[str] = []

    class Config(ConfigProperty.Config):
        """Model configuration."""

        extra = Extra.forbid
        title = "Runway Terraform Module args option"


class RunwayTerraformBackendConfigDataModel(ConfigProperty):
    """Model for Runway Terraform Module terraform_backend_config option."""

    bucket: Optional[str] = None
    dynamodb_table: Optional[str] = None
    region: Optional[str] = None

    class Config(ConfigProperty.Config):
        """Model configuration."""

        extra = Extra.forbid
        title = "Runway Terraform Module terraform_backend_config option"

    def __bool__(self) -> bool:
        """Evaluate the boolean value of the object instance."""
        data = self.dict(exclude_none=True)
        return "bucket" in data or "dynamodb_table" in data


class RunwayTerraformModuleOptionsDataModel(ConfigProperty):
    """Model for Runway Terraform Module options."""

    args: RunwayTerraformArgsDataModel = RunwayTerraformArgsDataModel()
    backend_config: RunwayTerraformBackendConfigDataModel = Field(
        RunwayTerraformBackendConfigDataModel(), alias="terraform_backend_config"
    )
    version: Optional[str] = Field(None, alias="terraform_version")
    workspace: Optional[str] = Field(None, alias="terraform_workspace")
    write_auto_tfvars: bool = Field(False, alias="terraform_write_auto_tfvars")

    class Config(ConfigProperty.Config):
        """Model configuration."""

        extra = Extra.ignore
        title = "Runway Terraform Module options"

    @validator("args", pre=True)
    def _convert_args(
        cls, v: Union[List[str], Dict[str, List[str]]]
    ) -> Dict[str, List[str]]:
        """Convert args from list to dict."""
        if isinstance(v, list):
            return {"apply": v}
        return v
