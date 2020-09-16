"""Base models & other objects."""
from __future__ import annotations

from typing import Any

import pydantic


class ConfigProperty(pydantic.BaseModel):
    """Base class for Runway configuration properties."""

    def get(self, key: str, default: Any = None) -> Any:
        """Implement evaluation of self.get.

        Args:
            key: Attribute name to return the value for.
            default: Value to return if attribute is not found.

        """
        return getattr(self, key, default)

    def __getitem__(self, key: str) -> Any:
        """Implement evaluation of self[key].

        Args:
            key: Attribute name to return the value for.

        Returns:
            The value associated with the provided key/attribute name.

        Raises:
            AttributeError: If attribute does not exist on this object.

        """
        return getattr(self, key)
