"""Serverless Hello World function."""

from __future__ import annotations

import json
from typing import Any


def handler(event: Any, context: Any) -> dict[str, int | str]:  # noqa: ARG001
    """Return Serverless Hello World."""
    body = {
        "message": "Go Serverless v1.0! Your function executed successfully!",
        "input": event,
    }
    return {"statusCode": 200, "body": json.dumps(body)}

    # Use this code if you don't use the http event with the LAMBDA-PROXY
    # integration
    # return {
    #     "message": "Go Serverless v1.0! Your function executed!",
    #     "event": event
    # }
