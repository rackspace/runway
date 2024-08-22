"""Runway Kubernetes Module options."""

from __future__ import annotations

from pathlib import Path

from pydantic import ConfigDict

from ...base import ConfigProperty


class RunwayK8sModuleOptionsDataModel(ConfigProperty):
    """Model for Runway Kubernetes Module options."""

    model_config = ConfigDict(
        extra="ignore",
        title="Runway Kubernetes Module options",
        validate_default=True,
        validate_assignment=True,
    )

    kubectl_version: str | None = None
    overlay_path: Path | None = None
