"""Type definitions."""
from __future__ import annotations

import sys
from typing import Any, Dict, Optional

if sys.version_info < (3, 8):
    from typing_extensions import Literal, TypedDict  # type: ignore
else:
    from typing import Literal, TypedDict  # type: ignore


class _LambdaResponeOptional(TypedDict, total=False):
    """Optional fields for a Lambda Response."""

    error: LambdaError


class _LambdaResponeRequired(TypedDict):
    """Required fields for a Lambda Response."""

    code: int
    data: Dict[str, Any]
    message: Optional[str]
    status: Literal["error", "success"]


class LambdaResponse(_LambdaResponeRequired, _LambdaResponeOptional):
    """Response from Lambda Function."""


class LambdaError(TypedDict, total=False):
    """Lambda Function error."""

    message: str
    reason: str
