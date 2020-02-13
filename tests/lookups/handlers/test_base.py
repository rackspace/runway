"""Tests for lookup handler base class."""
from unittest import TestCase

from runway.lookups.handlers.base import LookupHandler


class TestLookupHandler(TestCase):
    """Tests for LookupHandler."""

    def test_abstract_handle(self):
        """Handle should not be implimented."""
        with self.assertRaises(NotImplementedError):
            LookupHandler.handle(None, None)

    def test_parse(self):
        """Basic value parsing."""
        expected_query = 'my_query'

        result_query, result_args = LookupHandler.parse(expected_query)

        self.assertEqual(result_query, expected_query)
        self.assertEqual(result_args, {})

    def test_parse_args(self):
        """Parse query and args from value."""
        expected_args = {
            'key1': 'val1'
        }
        expected_query = 'my_query'
        value = '{}::{}'.format(expected_query, ','.join([
            '{}={}'.format(key, val) for key, val in expected_args.items()
        ]))

        result_query, result_args = LookupHandler.parse(value)

        self.assertEqual(result_query, expected_query)
        self.assertEqual(result_args, expected_args)

    def test_transform_bool_to_bool(self):
        """Bool should be returned as is."""
        result_true = LookupHandler.transform(True, to_type='bool')
        result_false = LookupHandler.transform(False, to_type='bool')

        self.assertTrue(result_true)
        self.assertFalse(result_false)

    def test_transform_str_to_bool(self):
        """String should be transformed using strtobool."""
        result_true = LookupHandler.transform('true', to_type='bool')
        result_false = LookupHandler.transform('false', to_type='bool')

        self.assertTrue(result_true)
        self.assertFalse(result_false)

    def test_transform_type_check(self):
        """Transform to bool type check."""
        with self.assertRaises(TypeError, msg='dict should raise an error'):
            LookupHandler.transform({'key1': 'val1'}, to_type='bool')

        with self.assertRaises(TypeError, msg='list should raise an error'):
            LookupHandler.transform(['li1'], to_type='bool')

        with self.assertRaises(TypeError, msg='number should raise an error'):
            LookupHandler.transform(10, to_type='bool')

        with self.assertRaises(TypeError, msg='float should raise an error'):
            LookupHandler.transform(10.0, to_type='bool')

        with self.assertRaises(TypeError, msg='NoneType should raise an error'):
            LookupHandler.transform(None, to_type='bool')

    def test_transform_str_direct(self):
        """Test types that are directly transformed to strings."""
        self.assertEqual(LookupHandler.transform('test', 'str'), 'test')
        self.assertEqual(LookupHandler.transform({'key1': 'val1'}, 'str'),
                         "{'key1': 'val1'}")
        self.assertEqual(LookupHandler.transform(True, 'str'), 'True')

    def test_transform_str_list(self):
        """Test list type joined to create string."""
        self.assertEqual(
            LookupHandler.transform(['val1', 'val2'], to_type='str'),
            'val1,val2'
        )
        self.assertEqual(
            LookupHandler.transform(set(['val', 'val']), to_type='str'),
            'val'
        )
        self.assertEqual(
            LookupHandler.transform(('val1', 'val2'), to_type='str'),
            'val1,val2'
        )

    def test_transform_str_list_delimiter(self):
        """Test list to string with a specified delimiter."""
        self.assertEqual(
            LookupHandler.transform(['val1', 'val2'], to_type='str',
                                    delimiter='|'),
            'val1|val2'
        )
