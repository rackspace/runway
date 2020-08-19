"""Tests for lookup handler for env."""
from unittest import TestCase

from runway.lookups.handlers.env import EnvLookup
from runway.util import MutableMap

CONTEXT = MutableMap(**{"env_vars": {"str_val": "test"}})


class TestEnvLookup(TestCase):
    """Tests for EnvLookup."""

    def test_handle(self):
        """Validate handle base functionality."""
        query = "str_val"
        result = EnvLookup.handle(query, context=CONTEXT)

        self.assertEqual(result, "test")

    def test_handle_not_found(self):
        """Validate exception when lookup cannot be resolved."""
        query = "NOT_VALID"

        with self.assertRaises(ValueError):
            EnvLookup.handle(query, context=CONTEXT)
