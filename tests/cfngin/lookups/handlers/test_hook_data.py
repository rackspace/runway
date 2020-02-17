"""Tests for runway.cfngin.lookups.handlers.hook_data."""
import unittest

from runway.cfngin.context import Context
from runway.cfngin.lookups.handlers.hook_data import HookDataLookup


class TestHookDataLookup(unittest.TestCase):
    """Tests for runway.cfngin.lookups.handlers.hook_data.HookDataLookup."""

    def setUp(self):
        """Run before tests."""
        self.ctx = Context({"namespace": "test-ns"})
        self.ctx.set_hook_data("fake_hook", {"result": "good"})

    def test_valid_hook_data(self):
        """Test valid hook data."""
        value = HookDataLookup.handle("fake_hook::result", context=self.ctx)
        self.assertEqual(value, "good")

    def test_invalid_hook_data(self):
        """Test invalid hook data."""
        with self.assertRaises(KeyError):
            HookDataLookup.handle("fake_hook::bad_key", context=self.ctx)

    def test_bad_value_hook_data(self):
        """Test bad value hook data."""
        with self.assertRaises(ValueError):
            HookDataLookup.handle("fake_hook", context=self.ctx)
