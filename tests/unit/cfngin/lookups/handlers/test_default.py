"""Tests for runway.cfngin.lookups.handlers.default."""

# pyright: basic
import unittest

from mock import MagicMock

from runway.cfngin.lookups.handlers.default import DefaultLookup
from runway.context import CfnginContext


class TestDefaultLookup(unittest.TestCase):
    """Tests for runway.cfngin.lookups.handlers.default.DefaultLookup."""

    def setUp(self) -> None:
        """Run before tests."""
        self.provider = MagicMock()
        self.context = CfnginContext(
            parameters={"namespace": "test", "env_var": "val_in_env"}
        )

    def test_env_var_present(self) -> None:
        """Test env var present."""
        lookup_val = "env_var::fallback"
        value = DefaultLookup.handle(
            lookup_val, provider=self.provider, context=self.context
        )
        assert value == "val_in_env"

    def test_env_var_missing(self) -> None:
        """Test env var missing."""
        lookup_val = "bad_env_var::fallback"
        value = DefaultLookup.handle(
            lookup_val, provider=self.provider, context=self.context
        )
        assert value == "fallback"

    def test_invalid_value(self) -> None:
        """Test invalid value."""
        with self.assertRaises(ValueError):
            value = "env_var:fallback"
            DefaultLookup.handle(value, provider=self.provider, context=self.context)
