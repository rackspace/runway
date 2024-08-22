"""AWS type definitions."""

from __future__ import annotations

from typing_extensions import TypedDict


class TagTypeDef(TypedDict):
    """AWS resource tags."""

    Key: str
    Value: str


TagSetTypeDef = list[TagTypeDef]
