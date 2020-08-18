"""Pytest fixtures and plugins."""
import pytest


@pytest.fixture
def patch_module_npm(monkeypatch):
    """Patch methods and functions used during init of RunwayModuleNpm."""
    monkeypatch.setattr("runway.module.RunwayModuleNpm.check_for_npm", lambda x: None)
    monkeypatch.setattr("runway.module.warn_on_boto_env_vars", lambda x: None)
