"""Base models & other objects."""
from __future__ import annotations

import pydantic

from ...utils import BaseModel


class ConfigProperty(BaseModel):
    """Base class for Runway configuration properties."""

    class Config(pydantic.BaseConfig):
        """Model configuration."""

        validate_all = True
        validate_assignment = True
