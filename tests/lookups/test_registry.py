"""Tests for lookup registry and common lookup functionality."""
# pylint: disable=no-self-use
from r4y.lookups.registry import RUNWAY_LOOKUP_HANDLERS
from r4y.util import MutableMap

VALUES = {
    'str_val': 'test'
}
CONTEXT = MutableMap(**{
    'env_vars': VALUES
})
VARIABLES = MutableMap(**VALUES)


class TestCommonLookupFunctionality(object):
    """Test common lookup functionally.

    All lookup handles should be able to pass these tests. Handling must
    be implement in all lookups in the "handle" method using the provided
    class methods of the "LookupHandler" base class.

    """

    def test_handle_default(self, r4y_context):
        """Verify default value is handled by lookups."""
        lookup_handlers = RUNWAY_LOOKUP_HANDLERS.copy()
        lookup_handlers.pop('ssm')  # requires special testing
        for _, lookup in lookup_handlers.items():
            query = 'NOT_VALID::default=default value'
            result = lookup.handle(query, context=r4y_context,
                                   variables=VARIABLES)

            assert result == 'default value'

    def test_handle_transform(self, r4y_context):
        """Verify transform is handled by lookup."""
        lookup_handlers = RUNWAY_LOOKUP_HANDLERS.copy()
        lookup_handlers.pop('ssm')  # requires special testing
        r4y_context.env_vars.update(VALUES)

        for _, lookup in lookup_handlers.items():
            query = 'NOT_VALID::default=false, transform=bool'
            result = lookup.handle(query, context=r4y_context,
                                   variables=VARIABLES)

            assert not result
