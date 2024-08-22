"""Base models & other objects."""

from __future__ import annotations

from pydantic import ConfigDict

from ...utils import BaseModel


class ConfigProperty(BaseModel):
    """Base class for Runway configuration properties."""

    model_config = ConfigDict(
        extra="ignore",
        validate_default=True,
        validate_assignment=True,
    )
