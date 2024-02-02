"""Mock lookup."""

from typing import Any

TYPE_NAME = "mock"


def handler(__value: Any, *, _: Any) -> str:
    """Mock handler."""
    return "mock"
