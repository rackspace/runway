"""Pytest configuration, fixtures, and plugins."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from _pytest.config import Config


# pylint: disable=unused-argument
def pytest_ignore_collect(path: Any, config: Config) -> bool:
    """Determine if this directory should have its tests collected."""
    return not config.option.functional
