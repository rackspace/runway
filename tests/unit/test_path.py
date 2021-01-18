"""Tests for the Path type object."""
# pylint: disable=no-self-use,redefined-outer-name,unused-argument
from __future__ import annotations

import logging
import pathlib
from typing import TYPE_CHECKING

import pytest

from runway.config.models.runway import RunwayModuleDefinitionModel
from runway.constants import DEFAULT_CACHE_DIR
from runway.path import Path
from runway.sources.source import Source

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

LOGGER = logging.getLogger("runway")

MODULE = "runway.path"


class MockGitSource(Source):
    """Mock a Git Source Object."""

    def fetch(self) -> pathlib.Path:
        """Fetch."""
        return pathlib.Path("mock/git/folder")


@pytest.fixture(scope="function")
def mock_git(mocker: MockerFixture) -> None:
    """Mock git."""
    mocker.patch(f"{MODULE}.Git", MockGitSource)


class TestPath:
    """Test Path class."""

    def test_parse_local_source_string(self) -> None:
        """Parsing location source string. Verify tuple is parsed as anticipated."""
        source, uri, location, options = Path.parse(
            RunwayModuleDefinitionModel(path="src/foo/bar")
        )
        assert source == "local"
        assert location == "src/foo/bar"
        assert uri == ""
        assert options == {}

    def test_parse_git_source_no_location_or_options(self) -> None:
        """Parsing Git source with no location or options.

        Verify tuple is parsed as anticipated.

        """
        source, uri, location, options = Path.parse(
            RunwayModuleDefinitionModel(
                path="git::git://github.com/onicagroup/foo/bar.git"
            )
        )
        assert source == "git"
        assert location == ""
        assert uri == "git://github.com/onicagroup/foo/bar.git"
        assert options == {}

    def test_parse_git_source_with_location_no_options(self) -> None:
        """Parsing Git source with location, no options. Verify tuple is parsed as anticipated."""
        source, uri, location, options = Path.parse(
            RunwayModuleDefinitionModel(
                path="git::git://github.com/onicagroup/foo/bar.git//foo/bar"
            )
        )
        assert source == "git"
        assert location == "foo/bar"
        assert uri == "git://github.com/onicagroup/foo/bar.git"
        assert options == {}

    def test_parse_git_source_with_options_no_location(self) -> None:
        """Parsing Git source with options, no location.

        Verify tuple is parsed as anticipated.

        """
        source, uri, location, options = Path.parse(
            RunwayModuleDefinitionModel(
                path="git::git://github.com/onicagroup/foo/bar.git?branch=foo"
            )
        )
        assert source == "git"
        assert location == ""
        assert uri == "git://github.com/onicagroup/foo/bar.git"
        assert options == {"branch": "foo"}

    def test_parse_git_source_with_multiple_options_no_location(self) -> None:
        """Parsing Git source with multiple options, no location.

        Verify tuple is parsed as anticipated.

        """
        source, uri, location, options = Path.parse(
            RunwayModuleDefinitionModel(
                path="git::git://github.com/onicagroup/foo/bar.git?branch=foo&bar=baz"
            )
        )
        assert source == "git"
        assert location == ""
        assert uri == "git://github.com/onicagroup/foo/bar.git"
        assert options == {"branch": "foo", "bar": "baz"}

    def test_parse_git_source_with_options_and_location(self) -> None:
        """Parsing Git source with options and location.

        Verify tuple is parsed as anticipated.

        """
        source, uri, location, options = Path.parse(
            RunwayModuleDefinitionModel(
                path="git::git://github.com/onicagroup/foo/bar.git//src/foo/bar?branch=foo"
            )
        )
        assert source == "git"
        assert location == "src/foo/bar"
        assert uri == "git://github.com/onicagroup/foo/bar.git"
        assert options == {"branch": "foo"}

    def test_parse_git_source_with_multiple_options_and_location(self) -> None:
        """Parsing Git source with multiple options and location.

        Verify tuple is parsed as anticipated.

        """
        path = "git::git://github.com/onicagroup/foo/bar.git//src/foo/bar?branch=foo&bar=baz"
        source, uri, location, options = Path.parse(
            RunwayModuleDefinitionModel(path=path)
        )
        assert source == "git"
        assert location == "src/foo/bar"
        assert uri == "git://github.com/onicagroup/foo/bar.git"
        assert options == {"branch": "foo", "bar": "baz"}

    def test_configuration_property(
        self, cd_tmp_path: pathlib.Path, mock_git: None
    ) -> None:
        """Verify the Configuration property is set to appropriate values."""
        path = "git::git://github.com/onicagroup/foo/bar.git//src/foo/bar?branch=foo"
        instance = Path(RunwayModuleDefinitionModel(path=path), cd_tmp_path)
        assert instance.configuration == {
            "source": "git",
            "location": "src/foo/bar",
            "uri": "git://github.com/onicagroup/foo/bar.git",
            "options": {"branch": "foo"},
            "cache_dir": DEFAULT_CACHE_DIR,
        }

    def test_module_root_set_to_env_root(
        self, cd_tmp_path: pathlib.Path, mock_git: None
    ) -> None:
        """When the path location == a root directory set to the env_root passed."""
        path = "."
        instance = Path(RunwayModuleDefinitionModel(path=path), cd_tmp_path)
        assert instance.module_root == cd_tmp_path

        path = "./"
        instance2 = Path(RunwayModuleDefinitionModel(path=path), cd_tmp_path)
        assert instance2.module_root == cd_tmp_path

    def test_module_root_set_to_contcatenated_path(
        self, cd_tmp_path: pathlib.Path, mock_git: None
    ) -> None:
        """Test module root set to concatednated path.

        When the path location is local and not the root combine the location
        with the env_root.

        """
        path = "foo/bar"
        instance = Path(RunwayModuleDefinitionModel(path=path), cd_tmp_path)
        assert instance.module_root == cd_tmp_path / path

    def test_module_root_set_to_fetched_source_value(
        self, cd_tmp_path: pathlib.Path, mock_git: None
    ) -> None:
        """When the path location is a remote resource fetch the directory."""
        path = "git::git://github.com/onicagroup/foo/bar.git//src/foo/bar?branch=foo"
        instance = Path(RunwayModuleDefinitionModel(path=path), cd_tmp_path)
        assert instance.module_root == pathlib.Path("mock/git/folder")
