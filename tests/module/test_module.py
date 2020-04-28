"""Test runway.module.__init__."""
# pylint: disable=no-self-use
import sys
from contextlib import contextmanager

import pytest

from runway.module import ModuleOptions


@contextmanager
def does_not_raise():
    """Use for conditional pytest.raises when using parametrize."""
    yield


class TestModuleOptions(object):
    """Test runway.module.ModuleOptions."""

    @pytest.mark.parametrize('data, env, expected, exception', [
        ('test', None, 'test', does_not_raise()),
        ('test', 'env', 'test', does_not_raise()),
        ({'key': 'value'}, 'test', {'key': 'called'}, does_not_raise()),
        ({'key': 'value'}, None, {'key': 'called'}, does_not_raise()),
        (['test'], None, ['test'], does_not_raise()),
        (['test'], 'env', ['test'], does_not_raise()),
        (None, None, None, does_not_raise()),
        (None, 'env', None, does_not_raise()),
        (100, None, None, pytest.raises(TypeError)),
        (100, 'env', None, pytest.raises(TypeError))
    ])
    @pytest.mark.skipif(sys.version_info.major < 3,
                        reason='python 2 does not handle unbound functions '
                        'being patched in')
    def test_merge_nested_env_dicts(self, monkeypatch, data, env,
                                    expected, exception):
        """Test merge_nested_env_dicts."""
        def merge_nested_environment_dicts(value, env_name):
            """Assert args passed to the method during parse."""
            assert value == list(data.values())[0]  # only pass data dict of 1 item
            assert env_name == env
            return 'called'

        monkeypatch.setattr('runway.module.merge_nested_environment_dicts',
                            merge_nested_environment_dicts)

        with exception:
            assert ModuleOptions.merge_nested_env_dicts(data, env) == expected

    def test_parse(self, runway_context):
        """Test parse."""
        with pytest.raises(NotImplementedError):
            assert ModuleOptions.parse(runway_context)

    @pytest.mark.parametrize('value', ['test', None, 123, {'key': 'val'}])
    def test_mutablemapping_abstractmethods(self, value):
        """Test the abstractmethods of MutableMapping."""
        obj = ModuleOptions()
        obj['key'] = value  # __setitem__
        assert obj['key'] == value, 'test __setitem__ and __getitem__'
        assert isinstance(obj['key'], type(value)), 'test type retention'
        assert obj.get('key') == value, 'ensure .get() is working'
        assert len(obj) == 1, 'test __len__'

        counter = 0
        for _ in obj:
            counter += 1
        assert counter == 1, 'test __iter__'

        del obj['key']
        assert 'key' not in obj, 'test __delitem__ with __contains__'
        with pytest.raises(KeyError):
            assert obj['key'], 'test __delitem__ with __getitem__'
