"""Tests for variables."""
from unittest import TestCase

from stacker.exceptions import UnresolvedVariable

from runway.variables import Variable
from runway.util import MutableMap


VALUE = {
    'test': 'success',
    'what': 'test',
    'bool_val': False,
    'dict_val': {'test': 'success'},
    'list_val': ['success']
}
CONTEXT = MutableMap(**{
    'env_vars': VALUE
})


class TestVariable(TestCase):
    """Test for variable resolution."""

    def test_value_simple_str(self):
        """Test value for a simple string without lookups."""
        var = Variable('test', 'success')

        self.assertTrue(var.resolved, msg='when no lookup is used, it should '
                        'be automatically marked as resolved')
        self.assertEqual(var.value, 'success')

    def test_value_simple_str_lookup(self):
        """Test value for simple str lookup."""
        var = Variable('test', '${env:test}')

        self.assertFalse(var.resolved)

        var.resolve(CONTEXT)

        self.assertTrue(var.resolved)
        self.assertEqual(var.value, VALUE['test'])

    def test_value_complex_str(self):
        """Multiple lookups should be usable within a single string."""
        var = Variable('test', 'the ${env:what} was ${env:test}ful')
        var.resolve(CONTEXT)

        self.assertEqual(var.value, 'the {} was {}ful'.format(VALUE['what'],
                                                              VALUE['test']))

    def test_value_nested_str(self):
        """Variable lookups should be resolvable within each other."""
        var = Variable('test', '${env:${env:what}}')
        var.resolve(CONTEXT)

        self.assertEqual(var.value, VALUE['test'])

    def test_value_lookup_in_dict(self):
        """Variable lookups should be resolvable when used in a dict."""
        var = Variable('test', {'my_dict': '${env:test}'})
        var.resolve(CONTEXT)

        self.assertEqual(var.value, {'my_dict': VALUE['test']})

    def test_value_lookup_in_list(self):
        """Variable lookups should be resolvable when used in a list."""
        var = Variable('test', ['${env:test}'])
        var.resolve(CONTEXT)

        self.assertEqual(var.value, [VALUE['test']])

    def test_value_lookup_to_bool(self):
        """Variable lookups should be resolvable to a bool."""
        var = Variable('test', '${env:bool_val}')
        var.resolve(CONTEXT)

        self.assertFalse(var.value)

    def test_value_lookup_to_dict(self):
        """Variable lookups should be resolvable to a dict value."""
        var = Variable('test', '${env:dict_val}')
        var.resolve(CONTEXT)

        # need to use data prop to compare the MutableMap contents
        self.assertEqual(var.value.data, VALUE['dict_val'])

    def test_value_lookup_to_list(self):
        """Variable lookups should be resolvable to a list value."""
        var = Variable('test', '${env:list_val}')
        var.resolve(CONTEXT)

        self.assertEqual(var.value, VALUE['list_val'])

    def test_value_unresolved(self):
        """Should raise `UnresolvedVariable`."""
        var = Variable('test', '${env:test}')

        with self.assertRaises(UnresolvedVariable):
            print(var.value)
