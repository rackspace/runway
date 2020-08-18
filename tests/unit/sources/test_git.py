"""Tests for the Source type object."""
import logging
import unittest

from runway.sources.git import Git

LOGGER = logging.getLogger("runway")


class GitTester(unittest.TestCase):
    """Tests for the Source type object."""

    def test_fetch_returns_directory_string(self):
        """Ensure a directory string is returned."""
        fetched = Git(
            **{
                "options": {},
                "uri": "git://github.com/onicagroup/runway.git",
                "location": "/",
            }
        ).fetch()
        self.assertEqual(fetched, "/")

    def test_sanitize_git_path(self):
        """Ensure git path is property sanitized."""
        path = Git().sanitize_git_path("git://github.com/onicagroup/runway.git")
        self.assertEqual(path, "github.com_onicagroup_runway")
