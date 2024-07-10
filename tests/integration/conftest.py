"""Pytest configuration, fixtures, and plugins."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

import pytest

if TYPE_CHECKING:
    from _pytest.config import Config

TEST_ROOT = Path(__file__).parent

CpConfigTypeDef = Callable[[str, Path], Path]


def pytest_ignore_collect(path: Any, config: Config) -> bool:
    """Determine if this directory should have its tests collected."""
    if config.option.functional:
        return True
    if config.option.markexpr and "wip" in config.option.markexpr:
        return False  # collect when looking for markers
    return not (config.option.integration or config.option.integration_only)


@pytest.fixture
def configs() -> Path:
    """Path to Runway config fixtures."""
    return TEST_ROOT.parent / "fixtures" / "configs"


@pytest.fixture
def cp_config(configs: Path) -> Callable[[str, Path], Path]:
    """Copy a config file."""

    def copy_config(config_name: str, dest_path: Path) -> Path:
        """Copy a config file by name to a destination directory.

        The resulting config will be named runway.yml.

        """
        runway_yml = dest_path / "runway.yml"
        if not config_name.startswith(".yml"):
            config_name += ".yml"
        shutil.copy(configs / config_name, runway_yml)
        return runway_yml

    return copy_config
