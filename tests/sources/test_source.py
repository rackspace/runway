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
