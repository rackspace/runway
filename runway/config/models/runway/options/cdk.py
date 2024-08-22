"""Runway AWS Cloud Development Kit Module options."""

from __future__ import annotations

from pydantic import ConfigDict

from ...base import ConfigProperty


class RunwayCdkModuleOptionsDataModel(ConfigProperty):
    """Model for Runway AWS Cloud Development Kit Module options."""

    model_config = ConfigDict(
        extra="ignore",
        title="Runway AWS Cloud Development Kit Module options",
        validate_default=True,
        validate_assignment=True,
    )

    build_steps: list[str] = []
    skip_npm_ci: bool = False
