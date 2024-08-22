"""Pytest configuration, fixtures, and plugins."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from .factories import cli_runner_factory

if TYPE_CHECKING:
    from collections.abc import Generator, Iterator

    from _pytest.config import Config
    from _pytest.config.argparsing import Parser
    from _pytest.fixtures import SubRequest
    from click.testing import CliRunner


def pytest_configure(config: Config) -> None:
    """Configure pytest."""
    config.addinivalue_line(  # cspell:ignore addinivalue
        "markers",
        "cli_runner(charset:='utf-8', env=None, echo_stdin=False, mix_stderr=True): "
        "Pass kwargs to `click.testing.CliRunner` initialization.",
    )


def pytest_addoption(parser: Parser) -> None:
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


@pytest.fixture()
def cli_runner(request: SubRequest) -> CliRunner:
    """Initialize instance of `click.testing.CliRunner`."""
    return cli_runner_factory(request)


@pytest.fixture()
def cli_runner_isolated(cli_runner: CliRunner) -> Generator[CliRunner, None, None]:
    """Initialize instance of `click.testing.CliRunner` with `isolate_filesystem()` called."""
    with cli_runner.isolated_filesystem():
        yield cli_runner


@pytest.fixture()
def cd_tmp_path(tmp_path: Path) -> Iterator[Path]:
    """Change directory to a temporary path.

    Returns:
        Path: Temporary path object.

    """
    prev_dir = Path.cwd()
    os.chdir(tmp_path)
    try:
        yield tmp_path
    finally:
        os.chdir(prev_dir)


@pytest.fixture()
def root_dir() -> Path:
    """Return a path object to the root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session", autouse=True)
def sanitize_environment() -> None:
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


@pytest.fixture(scope="session")
def tfenv_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Directory for storing tfenv between tests."""
    return tmp_path_factory.mktemp(".tfenv", numbered=True)
