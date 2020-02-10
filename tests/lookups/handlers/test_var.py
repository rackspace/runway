"""Tests for lookup handler for var."""
from unittest import TestCase

from runway.lookups.handlers.var import VarLookup
from runway.util import MutableMap

VARIABLES = MutableMap(**{
    'str_val': 'test',
    'false_val': False
})


class TestVarLookup(TestCase):
    """Tests for VarLookup."""

    def test_handle(self):
        """Validate handle base functionality."""
        query = 'str_val'
        result = VarLookup.handle(query, context=None, variables=VARIABLES)

        self.assertEqual(result, 'test')

    def test_handle_false_result(self):
        """Validate that a bool value of False can be resolved."""
        query = 'false_val'
        result = VarLookup.handle(query, context=None, variables=VARIABLES)

        self.assertFalse(result)

    def test_handle_not_found(self):
        """Validate exception when lookup cannot be resolved."""
        query = 'NOT_VALID'

        with self.assertRaises(ValueError):
            VarLookup.handle(query, context=None, variables=VARIABLES)
