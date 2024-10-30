"""Pytest fixtures and plugins."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def expected_yaml(local_fixtures: Path) -> Path:
    """Path to local fixtures expected yaml."""
    return local_fixtures / "expected_yaml"


@pytest.fixture
def local_fixtures() -> Path:
    """Local fixtures directory."""
    return Path(__file__).parent / "fixtures"
