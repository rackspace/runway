"""Version utilities."""

from __future__ import annotations

import packaging.version


class Version(packaging.version.Version):
    """Customize packaging.version.Version."""

    def __init__(self, version: str) -> None:
        """Instantiate class.

        Args:
            version: Version string. (e.g. 1.0.0, v1.0.0)

        """
        self._original_text = version
        super().__init__(version)

    def __repr__(self) -> str:
        """Return repr."""
        # this usage of super is required to reproduce the intended result in
        # any subclasses of this class
        return f"<Version('{super().__str__()}')>"

    def __str__(self) -> str:
        """Return the original version string."""
        return self._original_text
