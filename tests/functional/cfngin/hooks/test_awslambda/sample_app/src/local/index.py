"""Lambda Function."""

# pylint: disable=broad-except,unused-argument
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from ..type_defs import LambdaResponse

PACKAGE_DIR = Path(__file__).parent


def handler(event: Dict[str, Any], context: object) -> LambdaResponse:
    """Lambda Function entrypoint."""
    try:
        return {
            "code": 200,
            "data": {
                "dir_contents": [
                    str(path.relative_to(PACKAGE_DIR))
                    for path in sorted(PACKAGE_DIR.rglob("*"), reverse=True)
                ]
            },
            "message": None,
            "status": "success",
        }
    except Exception as exc:
        return {
            "code": 500,
            "data": {},
            "error": {"message": str(exc), "reason": type(exc).__name__},
            "message": None,
            "status": "error",
        }
