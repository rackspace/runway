"""Type definitions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from typing_extensions import TypeAlias

RunwayEnvironmentsType: TypeAlias = "dict[str, bool | list[str] | str]"
RunwayEnvironmentsUnresolvedType: TypeAlias = "dict[str, bool | list[str] | str] | str"
RunwayEnvVarsType: TypeAlias = "dict[str, list[str] | str]"
RunwayEnvVarsUnresolvedType: TypeAlias = "RunwayEnvVarsType | str"
RunwayModuleTypeTypeDef: TypeAlias = Literal[
    "cdk", "cloudformation", "kubernetes", "serverless", "static", "terraform"
]
