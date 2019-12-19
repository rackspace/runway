"""Tests for the Source type object."""
import logging
import os
import unittest

from runway.sources.source import Source

LOGGER = logging.getLogger('runway')


class SourceTester(unittest.TestCase):
    """Tests for the Source type object."""

    def test_fetch_not_implemented(self):
        """#fetch: By default a not implemented error should be thrown."""
        source = Source({})
        self.assertRaises(NotImplementedError, source.fetch)

    def test_when_no_cache_dir_parameter_in_config(self):
        """The default when no cache_dir is passed in the config"""
        source = Source({})
        self.assertEqual(source.cache_dir, os.path.expanduser('~/.runway_cache'))

    def test_a_cache_directory_is_created(self):
        """Ensure a cache directory is created"""
        source = Source({})
        self.assertTrue(os.path.isdir(source.cache_dir))

    def test_directory_path_is_properly_sanitized(self):
        """Ensure that path values are sanitized for folder creation."""
        dir_path = Source.sanitize_directory_path('foo@bar/baz:bop')
        self.assertEqual(dir_path, 'foo_bar_baz_bop')
