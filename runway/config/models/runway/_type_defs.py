"""Type definitions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Union

if TYPE_CHECKING:
    from typing_extensions import TypeAlias

RunwayEnvironmentsType: TypeAlias = dict[str, Union[bool, list[str], str]]
RunwayEnvironmentsUnresolvedType: TypeAlias = Union[dict[str, Union[bool, list[str], str]], str]
RunwayEnvVarsType: TypeAlias = dict[str, Union[list[str], str]]
RunwayEnvVarsUnresolvedType: TypeAlias = Union[RunwayEnvVarsType, str]
RunwayModuleTypeTypeDef: TypeAlias = Literal[
    "cdk", "cloudformation", "kubernetes", "serverless", "static", "terraform"
]
