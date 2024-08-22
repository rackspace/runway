"""Type definitions."""

from __future__ import annotations

from typing import Any, Literal, TypedDict


class _LambdaResponseOptional(TypedDict, total=False):
    """Optional fields for a Lambda Response."""

    error: LambdaError


class _LambdaResponseRequired(TypedDict):
    """Required fields for a Lambda Response."""

    code: int
    data: dict[str, Any]
    message: str | None
    status: Literal["error", "success"]


class LambdaResponse(_LambdaResponseRequired, _LambdaResponseOptional):
    """Response from Lambda Function."""


class LambdaError(TypedDict, total=False):
    """Lambda Function error."""

    message: str
    reason: str
