"""Tests for runway.cfngin.lookups.handlers.split."""
import unittest

from runway.cfngin.lookups.handlers.split import SplitLookup


class TestSplitLookup(unittest.TestCase):
    """Tests for runway.cfngin.lookups.handlers.split.SplitLookup."""

    def test_single_character_split(self):
        """Test single character split."""
        value = ",::a,b,c"
        expected = ["a", "b", "c"]
        assert SplitLookup.handle(value) == expected

    def test_multi_character_split(self):
        """Test multi character split."""
        value = ",,::a,,b,c"
        expected = ["a", "b,c"]
        assert SplitLookup.handle(value) == expected

    def test_invalid_value_split(self):
        """Test invalid value split."""
        value = ",:a,b,c"
        with self.assertRaises(ValueError):
            SplitLookup.handle(value)
