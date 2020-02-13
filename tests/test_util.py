"""Test Runway utils."""
# pylint: disable=no-self-use
import os.path
import string

from runway.util import MutableMap, load_object_from_string

VALUE = {
    'bool_val': False,
    'dict_val': {'test': 'success'},
    'list_val': ['success'],
    'nested_val': {
        'dict_val': {'test': 'success'}
    },
    'str_val': 'test'
}


class TestMutableMap:
    """Test for the custom MutableMap data type."""

    def test_bool(self):
        """Validates the bool value.

        Also tests setting an attr using bracket notation.

        """
        mute_map = MutableMap()

        assert not mute_map

        mute_map['str_val'] = 'test'

        assert mute_map

    def test_data(self):
        """Validate the init process and retrieving sanitized data."""
        mute_map = MutableMap(**VALUE)

        assert mute_map.data == VALUE

    def test_delete(self):
        """Validate that keys can be deleted.

        Uses dot and bracket notation.

        Also tests `get` method.

        """
        mute_map = MutableMap(**VALUE)
        del mute_map.str_val
        del mute_map['dict_val']

        assert not mute_map.get('str_val')
        assert not mute_map.get('dict_val')

    def test_find(self):
        """Validate the `find` method with and without `ignore_cache`.

        Also tests the `clear_found_cache` method and setting an attr value
        using dot notation.

        """
        mute_map = MutableMap(**VALUE)

        assert mute_map.find('str_val') == VALUE['str_val']

        mute_map.str_val = 'new_val'

        assert mute_map.find('str_val') == VALUE['str_val']
        assert mute_map.find('str_val', ignore_cache=True) == 'new_val'

        mute_map.clear_found_cache()

        assert mute_map.find('str_val') == 'new_val'

    def test_find_default(self):
        """Validate default value functionality."""
        mute_map = MutableMap(**VALUE)

        assert mute_map.find('NOT_VALID', 'default_val') == \
            'default_val', 'default should be used'
        assert mute_map.find('str_val', 'default_val') == \
            VALUE['str_val'], 'default should be ignored'


def test_load_object_from_string():
    """Test load object from string."""
    tests = (
        ("string.Template", string.Template),
        ("os.path.basename", os.path.basename),
        ("string.ascii_letters", string.ascii_letters)
    )
    for test in tests:
        assert load_object_from_string(test[0]) is test[1]
