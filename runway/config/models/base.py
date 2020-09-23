"""Base models & other objects."""
from __future__ import annotations

from typing import Any

import pydantic


class ConfigProperty(pydantic.BaseModel):
    """Base class for Runway configuration properties."""

    class Config:  # pylint: disable=too-few-public-methods
        """Model configuration."""

        validate_all = True
        validate_assignment = True

    def get(self, name: str, default: Any = None) -> Any:
        """Implement evaluation of self.get.

        Args:
            name: Attribute name to return the value for.
            default: Value to return if attribute is not found.

        """
        return getattr(self, name, default)

    def __contains__(self, name: str) -> bool:
        """Implement evaluation of 'in' conditional.

        Args:
            name: The name to check for existence in the model.

        """
        return name in self.__dict__

    def __getitem__(self, name: str) -> Any:
        """Implement evaluation of self[name].

        Args:
            name: Attribute name to return the value for.

        Returns:
            The value associated with the provided name/attribute name.

        Raises:
            AttributeError: If attribute does not exist on this object.

        """
        return getattr(self, name)

    def __setitem__(self, name: str, value: Any) -> None:
        """Implement item assignment (e.g. ``self[name] = value``).

        Args:
            name: Attribute name to set.
            value: Value to assign to the attribute.

        """
        super().__setattr__(name, value)
