"""Tests for runway.cfngin.lookups.handlers.split."""

import unittest

import pytest

from runway.cfngin.lookups.handlers.split import SplitLookup


class TestSplitLookup(unittest.TestCase):
    """Tests for runway.cfngin.lookups.handlers.split.SplitLookup."""

    def test_single_character_split(self) -> None:
        """Test single character split."""
        value = ",::a,b,c"
        expected = ["a", "b", "c"]
        assert SplitLookup.handle(value) == expected

    def test_multi_character_split(self) -> None:
        """Test multi character split."""
        value = ",,::a,,b,c"
        expected = ["a", "b,c"]
        assert SplitLookup.handle(value) == expected

    def test_invalid_value_split(self) -> None:
        """Test invalid value split."""
        value = ",:a,b,c"
        with pytest.raises(ValueError):  # noqa: PT011
            SplitLookup.handle(value)
