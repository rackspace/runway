"""Pytest configuration, fixtures, and plugins."""

# pylint: disable=redefined-outer-name
from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Generator

import pytest

if TYPE_CHECKING:
    from _pytest.fixtures import SubRequest


@pytest.fixture(scope="package")
def fixture_dir() -> Path:
    """Path to the fixture directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="function")
def local_backend(
    fixture_dir: Path, request: SubRequest
) -> Generator[Path, None, None]:
    """Copy local_backend.tf into the test directory."""
    file_name = "local_backend.tf"
    og_file = fixture_dir / file_name
    new_file = request.path.parent / file_name
    shutil.copy(og_file, new_file)
    yield new_file
    new_file.unlink()


@pytest.fixture(scope="function")
def no_backend(fixture_dir: Path, request: SubRequest) -> Generator[Path, None, None]:
    """Copy no_backend.tf into the test directory."""
    file_name = "no_backend.tf"
    og_file = fixture_dir / file_name
    new_file = request.path.parent / file_name
    shutil.copy(og_file, new_file)
    yield new_file
    new_file.unlink()


@pytest.fixture(scope="function")
def s3_backend(fixture_dir: Path, request: SubRequest) -> Generator[Path, None, None]:
    """Copy s3_backend.tf into the test directory."""
    file_name = "s3_backend.tf"
    og_file = fixture_dir / file_name
    new_file = request.path.parent / file_name
    shutil.copy(og_file, new_file)
    yield new_file
    new_file.unlink()
