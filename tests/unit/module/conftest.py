"""Pytest fixtures and plugins."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture
def patch_module_npm(mocker: MockerFixture) -> None:
    """Patch methods and functions used during init of RunwayModuleNpm."""
    mocker.patch("runway.module.base.RunwayModuleNpm.check_for_npm")
    mocker.patch("runway.module.base.RunwayModuleNpm.warn_on_boto_env_vars")
