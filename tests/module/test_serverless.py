"""Test runway.module.serverless."""
# pylint: disable=no-self-use,unused-argument
import pytest

from runway.module.serverless import ServerlessOptions


@pytest.mark.usefixtures('patch_module_npm')
class TestServerless(object):
    """Test runway.module.serverless.Serverless."""


class TestServerlessOptions(object):
    """Test runway.module.serverless.ServerlessOptions."""

    @pytest.mark.parametrize('args, expected', [
        (['--config', 'something'], ['--config', 'something']),
        (['--config', 'something', '--unknown-arg', 'value'],
         ['--config', 'something', '--unknown-arg', 'value']),
        (['-c', 'something'], ['--config', 'something']),
        (['-u'], ['-u'])
    ])
    def test_args(self, args, expected):
        """Test args."""
        obj = ServerlessOptions(args=args,
                                extend_serverless_yml={},
                                promotezip={})
        assert obj.args == expected

    @pytest.mark.parametrize('config', [
        ({'args': ['--config', 'something']}),
        ({'extend_serverless_yml': {'new_key': 'test_value'}}),
        ({'promotezip': {'bucketname': 'test-bucket'}}),
        ({'skip_npm_ci': True}),
        ({'args': ['--config', 'something'],
          'extend_serverless_yml': {'new_key': 'test_value'}}),
        ({'args': ['--config', 'something'],
          'extend_serverless_yml': {'new_key': 'test_value'},
          'promotezip': {'bucketname': 'test-bucket'}}),
        ({'args': ['--config', 'something'],
          'extend_serverless_yml': {'new_key': 'test_value'},
          'promotezip': {'bucketname': 'test-bucket'},
          'skip_npm_ci': True}),
        ({'args': ['--config', 'something'],
          'extend_serverless_yml': {'new_key': 'test_value'},
          'promotezip': {'bucketname': 'test-bucket'},
          'skip_npm_ci': False})
    ])
    def test_parse(self, config):
        """Test parse."""
        obj = ServerlessOptions.parse(**config)

        assert obj.args == config.get('args', [])
        assert obj.extend_serverless_yml == \
            config.get('extend_serverless_yml', {})
        assert obj.promotezip == config.get('promotezip', {})
        assert obj.skip_npm_ci == config.get('skip_npm_ci', False)

    def test_parse_invalid_promotezip(self):
        """Test parse with invalid promotezip value."""
        with pytest.raises(ValueError):
            assert not ServerlessOptions.parse(promotezip={'key': 'value'})

    def test_update_args(self):
        """Test update_args."""
        obj = ServerlessOptions(args=['--config', 'something',
                                      '--unknown-arg', 'value'],
                                extend_serverless_yml={},
                                promotezip={})
        assert obj.args == ['--config', 'something',
                            '--unknown-arg', 'value']

        obj.update_args('config', 'something-else')
        assert obj.args == ['--config', 'something-else',
                            '--unknown-arg', 'value']

        with pytest.raises(KeyError):
            obj.update_args('invalid-key', 'anything')
