"""Tests for the Path type object."""
import logging
import unittest

from runway.path import Path
from runway.sources.source import Source

LOGGER = logging.getLogger("runway")


class MockGitSource(Source):
    """Mock a Git Source Object."""

    def fetch(self):
        """Fetch."""
        return "mock/git/folder"


class PathTester(unittest.TestCase):
    """Test Path class."""

    def test_parse_local_source_string(self):
        """Parsing location source string. Verify tuple is parsed as anticipated."""
        source, uri, location, options = Path.parse({"path": "src/foo/bar"})
        self.assertEqual(source, "local")
        self.assertEqual(location, "src/foo/bar")
        self.assertEqual(uri, "")
        self.assertEqual(options, {})

    def test_parse_git_source_no_location_or_options(self):
        """Parsing Git source with no location or options.

        Verify tuple is parsed as anticipated.

        """
        source, uri, location, options = Path.parse(
            {"path": "git::git://github.com/onicagroup/foo/bar.git"}
        )
        self.assertEqual(source, "git")
        self.assertEqual(location, "")
        self.assertEqual(uri, "git://github.com/onicagroup/foo/bar.git")
        self.assertEqual(options, {})

    def test_parse_git_source_with_location_no_options(self):
        """Parsing Git source with location, no options. Verify tuple is parsed as anticipated."""
        source, uri, location, options = Path.parse(
            {"path": "git::git://github.com/onicagroup/foo/bar.git//foo/bar"}
        )
        self.assertEqual(source, "git")
        self.assertEqual(location, "foo/bar")
        self.assertEqual(uri, "git://github.com/onicagroup/foo/bar.git")
        self.assertEqual(options, {})

    def test_parse_git_source_with_options_no_location(self):
        """Parsing Git source with options, no location.

        Verify tuple is parsed as anticipated.

        """
        source, uri, location, options = Path.parse(
            {"path": "git::git://github.com/onicagroup/foo/bar.git?branch=foo"}
        )
        self.assertEqual(source, "git")
        self.assertEqual(location, "")
        self.assertEqual(uri, "git://github.com/onicagroup/foo/bar.git")
        self.assertEqual(options, {"branch": "foo"})

    def test_parse_git_source_with_multiple_options_no_location(self):
        """Parsing Git source with multiple options, no location.

        Verify tuple is parsed as anticipated.

        """
        source, uri, location, options = Path.parse(
            {"path": "git::git://github.com/onicagroup/foo/bar.git?branch=foo&bar=baz"}
        )
        self.assertEqual(source, "git")
        self.assertEqual(location, "")
        self.assertEqual(uri, "git://github.com/onicagroup/foo/bar.git")
        self.assertEqual(options, {"branch": "foo", "bar": "baz"})

    def test_parse_git_source_with_options_and_location(self):
        """Parsing Git source with options and location.

        Verify tuple is parsed as anticipated.

        """
        source, uri, location, options = Path.parse(
            {
                "path": "git::git://github.com/onicagroup/foo/bar.git//src/foo/bar?branch=foo"
            }
        )
        self.assertEqual(source, "git")
        self.assertEqual(location, "src/foo/bar")
        self.assertEqual(uri, "git://github.com/onicagroup/foo/bar.git")
        self.assertEqual(options, {"branch": "foo"})

    def test_parse_git_source_with_multiple_options_and_location(self):
        """Parsing Git source with multiple options and location.

        Verify tuple is parsed as anticipated.

        """
        path = "git::git://github.com/onicagroup/foo/bar.git//src/foo/bar?branch=foo&bar=baz"
        source, uri, location, options = Path.parse({"path": path})
        self.assertEqual(source, "git")
        self.assertEqual(location, "src/foo/bar")
        self.assertEqual(uri, "git://github.com/onicagroup/foo/bar.git")
        self.assertEqual(options, {"branch": "foo", "bar": "baz"})

    def test_configuration_property(self):
        """Verify the Configuration property is set to appropriate values."""
        path = "git::git://github.com/onicagroup/foo/bar.git//src/foo/bar?branch=foo"
        instance = Path({"path": path}, "fake/env/root", git_source_class=MockGitSource)
        self.assertEqual(
            instance.configuration,
            {
                "source": "git",
                "location": "src/foo/bar",
                "uri": "git://github.com/onicagroup/foo/bar.git",
                "options": {"branch": "foo"},
                "cache_dir": None,
            },
        )

    def test_module_root_set_to_env_root(self):
        """When the path location == a root directory set to the env_root passed."""
        path = "."
        instance = Path({"path": path}, "fake/env/root", git_source_class=MockGitSource)
        self.assertEqual(instance.module_root, "fake/env/root")

        path = "./"
        instance2 = Path(
            {"path": path}, "fake/env/root", git_source_class=MockGitSource
        )
        self.assertEqual(instance2.module_root, "fake/env/root")

    def test_module_root_set_to_contcatenated_path(self):
        """Test module root set to concatednated path.

        When the path location is local and not the root combine the location
        with the env_root.

        """
        path = "foo/bar"
        instance = Path({"path": path}, "fake/env/root", git_source_class=MockGitSource)
        self.assertEqual(instance.module_root, "fake/env/root/foo/bar")

    def test_module_root_set_to_fetched_source_value(self):
        """When the path location is a remote resource fetch the directory."""
        path = "git::git://github.com/onicagroup/foo/bar.git//src/foo/bar?branch=foo"
        instance = Path({"path": path}, "fake/env/root", git_source_class=MockGitSource)
        self.assertEqual(instance.module_root, "mock/git/folder")
