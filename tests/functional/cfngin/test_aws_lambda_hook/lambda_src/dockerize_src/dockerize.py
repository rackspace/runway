"""Test handler."""  # noqa: INP001

from __future__ import annotations

from typing import Any

import lib  # type: ignore


def handler(event: Any, context: Any) -> dict[str, int | str]:  # noqa: ARG001
    """Handle lambda."""
    try:
        if lib.RESPONSE_OBJ.shape == (3, 5):
            return {"statusCode": 200, "body": str(lib.RESPONSE_OBJ.shape)}  # type: ignore
        raise ValueError
    except:  # noqa: E722
        return {"statusCode": 500, "body": "fail"}
