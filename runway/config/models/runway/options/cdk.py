"""Runway AWS Cloud Development Kit Module options."""
from __future__ import annotations

from typing import List

from pydantic import Extra

from ...base import ConfigProperty


class RunwayCdkModuleOptionsDataModel(ConfigProperty):
    """Model for Runway AWS Cloud Development Kit Module options."""

    build_steps: List[str] = []
    skip_npm_ci: bool = False

    class Config(ConfigProperty.Config):
        """Model configuration."""

        extra = Extra.ignore
        title = "Runway AWS Cloud Development Kit Module options."
