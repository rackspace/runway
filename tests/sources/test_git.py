"""Tests for the Source type object."""
import logging
import unittest

from r4y.sources.git import Git

LOGGER = logging.getLogger('r4y')


class GitTester(unittest.TestCase):
    """Tests for the Source type object."""

    def test_fetch_returns_directory_string(self):
        """Ensure a directory string is returned."""
        fetched = Git(**{
            'options': {},
            'uri': 'git://github.com/onicagroup/r4y.git',
            'location': '/'
        }).fetch()
        self.assertEqual(fetched, '/')

    def test_sanitize_git_path(self):
        """Ensure git path is property sanitized"""
        path = Git().sanitize_git_path('git://github.com/onicagroup/r4y.git')
        self.assertEqual(path, 'github.com_onicagroup_r4y')
