"""Pytest configuration, fixtures, and plugins."""
# pylint: disable=redefined-outer-name
import shutil
from pathlib import Path

import pytest

TEST_ROOT = Path(__file__).parent


def pytest_ignore_collect(path, config):  # pylint: disable=unused-argument
    """Determine if this directory should have its tests collected."""
    if config.option.functional:
        return True
    return not (config.option.integration or config.option.integration_only)


@pytest.fixture
def configs():
    """Path to Runway config fixtures."""
    return TEST_ROOT.parent / "fixtures" / "configs"


@pytest.fixture
def cp_config(configs):
    """Copy a config file."""

    def copy_config(config_name, dest_path):
        """Copy a config file by name to a destination directory.

        The resulting config will be named runway.yml.

        """
        runway_yml = dest_path / "runway.yml"
        if not config_name.startswith(".yml"):
            config_name += ".yml"
        shutil.copy(configs / config_name, runway_yml)
        return runway_yml

    return copy_config
