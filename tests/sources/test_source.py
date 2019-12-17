"""Tests for the Source type object."""
import logging
import unittest

from runway.sources.source import Source

LOGGER = logging.getLogger('runway')


class SourceTester(unittest.TestCase):
    """Tests for the Source type object."""

    def test_fetch_not_implemented(self):
        """#fetch: By default a not implemented error should be thrown."""
        source = Source({})
        self.assertRaises(NotImplementedError, source.fetch)
