"""Pytest fixtures and plugins."""
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch


@pytest.fixture
def patch_module_npm(monkeypatch: MonkeyPatch) -> None:
    """Patch methods and functions used during init of RunwayModuleNpm."""
    monkeypatch.setattr("runway.module.RunwayModuleNpm.check_for_npm", lambda x: None)
    monkeypatch.setattr("runway.module.warn_on_boto_env_vars", lambda x: None)
