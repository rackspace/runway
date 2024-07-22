"""Lambda Function."""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..type_defs import LambdaResponse

PACKAGE_DIR = Path(__file__).parent


def handler(event: dict[str, Any], context: object) -> LambdaResponse:  # noqa: ARG001
    """Lambda Function entrypoint."""
    try:
        import lxml  # type: ignore
        import xmlsec  # type: ignore

        return {
            "code": 200,
            "data": {
                "dir_contents": [
                    str(path.relative_to(PACKAGE_DIR))
                    for path in sorted(PACKAGE_DIR.rglob("*"), reverse=True)
                ],
                "lxml": [i[0] for i in inspect.getmembers(lxml)],  # type: ignore
                "xmlsec": [i[0] for i in inspect.getmembers(xmlsec)],  # type: ignore
            },
            "message": None,
            "status": "success",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "code": 500,
            "data": {
                "dir_contents": [
                    str(path.relative_to(PACKAGE_DIR))
                    for path in sorted(PACKAGE_DIR.rglob("*"), reverse=True)
                ]
            },
            "error": {"message": str(exc), "reason": type(exc).__name__},
            "message": None,
            "status": "error",
        }
