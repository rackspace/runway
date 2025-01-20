"""Mock lookup."""

from typing import Any

TYPE_NAME = "mock"


def handler(_value: Any, *, _: Any) -> str:
    """Mock handler."""
    return "mock"
