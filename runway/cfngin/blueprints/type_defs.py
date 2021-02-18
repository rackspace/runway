"""CFNgin Blueprint type definitions."""
from __future__ import annotations

from typing import Any, Callable, List

from typing_extensions import TypedDict


class _RequiredBlueprintVariableTypeDef(TypedDict, total=False):
    """Type definition for runway.cfngin.blueprints.base.Blueprint.VARIABLES items."""

    type: Any


class _OptionalBlueprintVariableTypeDef(TypedDict, total=False):
    """Type definition for runway.cfngin.blueprints.base.Blueprint.VARIABLES items."""

    allowed_pattern: str
    allowed_values: List[Any]
    constraint_description: str
    default: Any
    description: str
    max_length: int
    min_length: int
    min_value: int
    no_echo: bool
    validator: Callable[[Any], Any]


class BlueprintVariableTypeDef(
    _RequiredBlueprintVariableTypeDef, _OptionalBlueprintVariableTypeDef
):
    """Type definition for runway.cfngin.blueprints.base.Blueprint.VARIABLES items."""
