"""Tests for runway.cfngin.lookups.handlers.default."""
import unittest

from mock import MagicMock

from runway.cfngin.context import Context
from runway.cfngin.lookups.handlers.default import DefaultLookup


class TestDefaultLookup(unittest.TestCase):
    """Tests for runway.cfngin.lookups.handlers.default.DefaultLookup."""

    def setUp(self):
        """Run before tests."""
        self.provider = MagicMock()
        self.context = Context(
            environment={"namespace": "test", "env_var": "val_in_env"}
        )

    def test_env_var_present(self):
        """Test env var present."""
        lookup_val = "env_var::fallback"
        value = DefaultLookup.handle(
            lookup_val, provider=self.provider, context=self.context
        )
        assert value == "val_in_env"

    def test_env_var_missing(self):
        """Test env var missing."""
        lookup_val = "bad_env_var::fallback"
        value = DefaultLookup.handle(
            lookup_val, provider=self.provider, context=self.context
        )
        assert value == "fallback"

    def test_invalid_value(self):
        """Test invalid value."""
        with self.assertRaises(ValueError):
            value = "env_var:fallback"
            DefaultLookup.handle(value, provider=self.provider, context=self.context)
