"""Runway Kubernetes Module options."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import Extra

from ...base import ConfigProperty


class RunwayK8sModuleOptionsDataModel(ConfigProperty):
    """Model for Runway Kubernetes Module options."""

    kubectl_version: Optional[str] = None
    overlay_path: Optional[Path] = None

    class Config(ConfigProperty.Config):
        """Model configuration."""

        extra = Extra.ignore
        title = "Runway Kubernetes Module options."
