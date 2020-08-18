"""Pytest configuration, fixtures, and plugins."""
import os
import sys

import pytest

if sys.version_info.major > 2:
    from pathlib import Path  # pylint: disable=E
else:
    from pathlib2 import Path  # pylint: disable=E


def pytest_addoption(parser):
    """Add pytest CLI options."""
    parser.addoption(
        "--functional",
        action="store_true",
        default=False,
        help="run only functional tests",
    )
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="include integration tests in regular testing",
    )
    parser.addoption(
        "--integration-only",
        action="store_true",
        default=False,
        help="run only integration tests",
    )


@pytest.fixture(scope="function")
def cd_tmp_path(tmp_path):
    """Change directory to a temporary path.

    Returns:
        Path: Temporary path object.

    """
    prev_dir = os.getcwd()
    os.chdir(str(tmp_path))
    try:
        yield tmp_path
    finally:
        os.chdir(prev_dir)


@pytest.fixture(scope="function")
def root_dir():
    """Return a path object to the root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session", autouse=True)
def sanitize_environment():
    # type: () -> None
    """Remove variables from the environment that could interfere with tests."""
    env_vars = [
        "CI",
        "DEBUG",
        "DEPLOY_ENVIRONMENT",
        "CFNGIN_STACK_POLL_TIME",
        "RUNWAY_MAX_CONCURRENT_MODULES",
        "RUNWAY_MAX_CONCURRENT_REGIONS",
    ]
    for var in env_vars:
        os.environ.pop(var, None)
