"""Test Runway utils."""
# pylint: disable=no-self-use
import os
import string
import sys

from mock import MagicMock, patch

from runway.util import MutableMap, argv, environ, load_object_from_string

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


@patch.object(sys, 'argv', ['runway', 'deploy'])
def test_argv():
    """Test argv."""
    orig_expected = ['runway', 'deploy']
    override = ['stacker', 'build', 'test.yml']

    assert sys.argv == orig_expected, 'validate original value'

    with argv(*override):
        assert sys.argv == override, 'validate override'

    assert sys.argv == orig_expected, 'validate value returned to original'


@patch.object(os, 'environ', {'TEST_PARAM': 'initial value'})
def test_environ():
    """Test environ."""
    orig_expected = {'TEST_PARAM': 'initial value'}
    override = {'TEST_PARAM': 'override', 'new_param': 'value'}

    assert os.environ == orig_expected, 'validate original value'

    with environ(override):
        assert os.environ == override, 'validate override'

    assert os.environ == orig_expected, 'validate value returned to original'


def test_load_object_from_string():
    """Test load object from string."""
    tests = (
        ("string.Template", string.Template),
        ("os.path.basename", os.path.basename),
        ("string.ascii_letters", string.ascii_letters)
    )
    for test in tests:
        assert load_object_from_string(test[0]) is test[1]

    obj_path = 'tests.fixtures.mock_hooks.GLOBAL_VALUE'
    # check value from os.environ
    assert load_object_from_string(obj_path, try_reload=True) == 'us-east-1'

    with environ({'AWS_DEFAULT_REGION': 'us-west-2'}):
        # check value from os.environ after changing it to ensure reload
        assert load_object_from_string(obj_path, try_reload=True) == 'us-west-2'


@patch('runway.util.six')
def test_load_object_from_string_reload_conditions(mock_six):
    """Test load_object_from_string reload conditions."""
    mock_six.moves.reload_module.return_value = MagicMock()
    builtin_test = 'sys.version_info'
    mock_hook = 'tests.fixtures.mock_hooks.GLOBAL_VALUE'

    try:
        del sys.modules['tests.fixtures.mock_hooks']
    except:  # noqa pylint: disable=bare-except
        pass

    load_object_from_string(builtin_test, try_reload=False)
    mock_six.moves.reload_module.assert_not_called()

    load_object_from_string(builtin_test, try_reload=True)
    mock_six.moves.reload_module.assert_not_called()

    load_object_from_string(mock_hook, try_reload=True)
    mock_six.moves.reload_module.assert_not_called()

    load_object_from_string(mock_hook, try_reload=True)
    mock_six.moves.reload_module.assert_called_once()
