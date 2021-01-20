"""Context type definitions."""
from __future__ import annotations

from typing_extensions import TypedDict


class PersistentGraphLocation(TypedDict, total=False):
    """CFNgin persistent graph location."""

    Bucket: str
    Key: str
