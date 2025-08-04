"""Runway AWS SAM Module options."""

from __future__ import annotations

from pydantic import ConfigDict

from ...base import ConfigProperty


class RunwaySamModuleOptionsDataModel(ConfigProperty):
    """Model for Runway AWS SAM Module options."""

    model_config = ConfigDict(
        extra="ignore",
        title="Runway AWS SAM Module options",
        validate_default=True,
        validate_assignment=True,
    )

    build_args: list[str] = []
    deploy_args: list[str] = []
    skip_build: bool = False
