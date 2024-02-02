"""Pytest fixtures and plugins."""

# pylint: disable=redefined-outer-name
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(scope="function")
def expected_yaml(local_fixtures: Path) -> Path:
    """Path to local fixtures expected yaml."""
    return local_fixtures / "expected_yaml"


@pytest.fixture(scope="function")
def local_fixtures() -> Path:
    """Local fixtures directory."""
    return Path(__file__).parent / "fixtures"
