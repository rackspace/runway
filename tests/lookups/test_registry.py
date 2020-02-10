"""Tests for lookup registry and common lookup functionality."""
from unittest import TestCase

from runway.lookups.registry import RUNWAY_LOOKUP_HANDLERS
from runway.util import MutableMap

VALUES = {
    'str_val': 'test'
}
CONTEXT = MutableMap(**{
    'env_vars': VALUES
})
VARIABLES = MutableMap(**VALUES)


class TestCommonLookupFunctionality(TestCase):
    """Test common lookup functionally.

    All lookup handles should be able to pass these tests. Handling must
    be implement in all lookups in the "handle" method using the provided
    class methods of the "LookupHandler" base class.

    """

    def test_handle_default(self):
        """Verify default value is handled by lookups."""
        for name, lookup in RUNWAY_LOOKUP_HANDLERS.items():
            query = 'NOT_VALID::default=default value'
            result = lookup.handle(query, context=CONTEXT,
                                   variables=VARIABLES)

            self.assertEqual(result, 'default value',
                             msg='{} lookup should support the "default" arg '
                             'for default values.'.format(name))

    def test_handle_transform(self):
        """Verify transform is handled by lookup."""
        for name, lookup in RUNWAY_LOOKUP_HANDLERS.items():
            query = 'NOT_VALID::default=false, transform=bool'
            result = lookup.handle(query, context=CONTEXT,
                                   variables=VARIABLES)

            self.assertFalse(result, msg='{} lookup should support the '
                             '"transform" arg.'.format(name))
