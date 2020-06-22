"""Tests for context module."""
# pylint: disable=protected-access,no-self-use
import logging
import os

import boto3
import pytest
from botocore.stub import Stubber
from mock import patch

from runway.context import Context
from runway.util import environ

from .factories import MockBoto3Session

LOGGER = logging.getLogger('runway')

TEST_CREDENTIALS = {
    'AWS_ACCESS_KEY_ID': 'foo',
    'AWS_SECRET_ACCESS_KEY': 'bar',
    'AWS_SESSION_TOKEN': 'foobar'
}


class TestContext(object):
    """Test Context class."""

    def test_account_id(self, monkeypatch):
        """Test account_id."""
        account_id = '123456789012'
        client = boto3.client('sts')
        stubber = Stubber(client)
        mock_session = MockBoto3Session(clients={'sts.us-east-1': client},
                                        region_name='us-east-1')
        monkeypatch.setattr(Context, 'get_session', lambda self_: mock_session)
        context = Context(env_name='test',
                          env_region='us-east-1',
                          env_root='./',
                          env_vars={})

        stubber.add_response(method='get_caller_identity',
                             service_response={'UserId': 'test-user',
                                               'Account': account_id,
                                               'Arn': 'arn:aws:iam::{}:'
                                                      'user/test-user'
                                                      .format(account_id)})

        with stubber as stub:
            assert context.account_id == account_id
        stub.assert_no_pending_responses()

    def test_boto3_credentials(self):
        """Test boto3_credentials."""
        context = Context(env_name='test',
                          env_region='us-east-1',
                          env_root='./',
                          env_vars=TEST_CREDENTIALS.copy())

        assert context.boto3_credentials == {key.lower(): value
                                             for key, value in
                                             TEST_CREDENTIALS.items()}

    def test_current_aws_creds(self):
        """Test current_aws_creds."""
        context = Context(env_name='test',
                          env_region='us-east-1',
                          env_root='./',
                          env_vars=TEST_CREDENTIALS.copy())

        assert context.current_aws_creds == TEST_CREDENTIALS

    @pytest.mark.parametrize('colorize, isatty, expected', [
        (None, True, False),
        (None, False, True),
        (True, False, False),
        (False, True, True),
        ('true', False, False),
        ('false', True, True),
        (ValueError, True, False),
        (ValueError, False, True)
    ])
    @patch('runway.context.sys.stdout')
    def test_no_color(self, mock_stdout, colorize, isatty, expected):
        """Test no_color."""
        mock_stdout.isatty.return_value = isatty
        env_vars = {}
        if colorize is not None:
            env_vars['RUNWAY_COLORIZE'] = colorize
        ctx = Context('test', 'us-east-1', './tests', env_vars=env_vars)
        assert ctx.no_color == expected

    def test_is_interactive(self):
        """Test is_interactive."""
        context = Context(env_name='test',
                          env_region='us-east-1',
                          env_root='./',
                          env_vars={'NON_EMPTY': '1'})
        assert context.is_interactive

        context.env_vars['CI'] = '1'
        assert not context.is_interactive

    def test_is_noninteractive(self):
        """Test is_noninteractive."""
        context = Context(env_name='test',
                          env_region='us-east-1',
                          env_root='./',
                          env_vars={'NON_EMPTY': '1'})
        assert not context.is_noninteractive

        context.env_vars['CI'] = '1'
        assert context.is_noninteractive

    def test_is_python3(self):
        """Test is_python3."""
        from runway.context import sys
        context = Context(env_name='test',
                          env_region='us-east-1',
                          env_root='./')

        with patch.object(sys, 'version_info') as version_info:
            version_info.major = 2
            assert not context.is_python3

        with patch.object(sys, 'version_info') as version_info:
            version_info.major = 3
            assert context.is_python3

    def test_max_concurrent_cfngin_stacks(self):
        """Test max_concurrent_cfngin_stacks."""
        context = Context(env_name='test',
                          env_region='us-east-1',
                          env_root='./')
        assert context.max_concurrent_cfngin_stacks == 0

        context.env_vars['RUNWAY_MAX_CONCURRENT_CFNGIN_STACKS'] = '1'
        assert context.max_concurrent_cfngin_stacks == 1

    def test_max_concurrent_modules(self):
        """Test max_concurrent_modules."""
        context = Context(env_name='test',
                          env_region='us-east-1',
                          env_root='./',
                          env_vars={'RUNWAY_MAX_CONCURRENT_MODULES': '1'})
        assert context.max_concurrent_modules == 1

        del context.env_vars['RUNWAY_MAX_CONCURRENT_MODULES']

        with patch('runway.context.multiprocessing.cpu_count') as cpu_count:
            cpu_count.return_value = 8
            assert context.max_concurrent_modules == 8

    def test_max_concurrent_regions(self):
        """Test max_concurrent_regions."""
        context = Context(env_name='test',
                          env_region='us-east-1',
                          env_root='./',
                          env_vars={'RUNWAY_MAX_CONCURRENT_REGIONS': '1'})
        assert context.max_concurrent_regions == 1

        del context.env_vars['RUNWAY_MAX_CONCURRENT_REGIONS']

        with patch('runway.context.multiprocessing.cpu_count') as cpu_count:
            cpu_count.return_value = 8
            assert context.max_concurrent_regions == 8

    def test_use_concurrent(self):
        """Test use_concurrent."""
        from runway.context import sys
        context = Context(env_name='test',
                          env_region='us-east-1',
                          env_root='./',
                          env_vars={'NON_EMPTY': '1'})
        context_ci = Context(env_name='test',
                             env_region='us-east-1',
                             env_root='./',
                             env_vars={'CI': '1'})

        with patch.object(sys, 'version_info') as version_info:
            version_info.major = 2
            assert not context.use_concurrent
            assert not context_ci.use_concurrent

        with patch.object(sys, 'version_info') as version_info:
            version_info.major = 3
            assert not context.use_concurrent
            assert context_ci.use_concurrent

    def test_init_name_from_arg(self):
        """_env_name_from_env should be false when DEPLOY_ENVIRONMENT not set."""
        context = Context(env_name='test', env_region='us-east-1',
                          env_root='./')
        assert context.env_name == 'test'
        assert context.env_vars['DEPLOY_ENVIRONMENT'] == context.env_name, \
            'env_vars.DEPLOY_ENVIRONMENT should be set from env_name'
        assert not context._env_name_from_env, \
            'should be false when env_name was not derived from env_var'

    def test_init_from_envvar(self):
        """_env_name_from_env should be true when DEPLOY_ENVIRONMENT is set."""
        context = Context(env_name='test', env_region='us-east-1',
                          env_root='./', env_vars={'DEPLOY_ENVIRONMENT': 'test'})
        assert context.env_name == 'test'
        assert context.env_vars['DEPLOY_ENVIRONMENT'] == context.env_name, \
            'env_vars.DEPLOY_ENVIRONMENT should be set from env_name'
        assert context._env_name_from_env, \
            'should be true when env_name was not derived from env_var'

    def test_echo_detected_environment_not_env(self, caplog):
        """Environment helper note when DEPLOY_ENVIRONMENT is not set."""
        context = Context(env_name='test', env_region='us-east-1',
                          env_root='./')
        expected = ['',
                    'Environment "test" was determined from the '
                    'current git branch or parent directory.',
                    'If this is not the environment name, update '
                    'the branch/folder name or set an override value via the '
                    'DEPLOY_ENVIRONMENT environment variable',
                    '']

        with caplog.at_level(logging.INFO):
            context.echo_detected_environment()

        assert [rec.message for rec in caplog.records] == expected

    def test_echo_detected_environment_from_env(self, caplog):
        """Environment helper note when DEPLOY_ENVIRONMENT is set."""
        context = Context(env_name='test', env_region='us-east-1',
                          env_root='./', env_vars={'DEPLOY_ENVIRONMENT': 'test'})
        expected = ['',
                    'Environment "test" was determined from the '
                    'DEPLOY_ENVIRONMENT environment variable.',
                    'If this is not correct, update the value (or '
                    'unset it to fall back to the name of the current git '
                    'branch or parent directory).',
                    '']

        with caplog.at_level(logging.INFO):
            context.echo_detected_environment()

        assert [rec.message for rec in caplog.records] == expected

    def test_save_existing_iam_env_vars(self):
        """Test save_existing_iam_env_vars."""
        context = Context(env_name='dev', env_region='us-east-1',
                          env_root='./', env_vars=TEST_CREDENTIALS.copy())
        context.save_existing_iam_env_vars()
        assert context.env_vars['OLD_AWS_ACCESS_KEY_ID'] == 'foo'
        assert context.env_vars['OLD_AWS_SECRET_ACCESS_KEY'] == 'bar'
        assert context.env_vars['OLD_AWS_SESSION_TOKEN'] == 'foobar'

    def test_init(self, tmp_path):
        """Test init process."""
        env_name = 'test'
        env_region = 'us-east-1'
        env_root = str(tmp_path)
        config_file = tmp_path / 'config'
        config_file.write_text(u'[profile test]\n'
                               'aws_access_key_id = bar\n'
                               'aws_secret_access_key = foo')

        with environ(dict(AWS_PROFILE='test', **TEST_CREDENTIALS)):
            env_vars = os.environ.copy()
            env_vars['DEPLOY_ENVIRONMENT'] = env_name

            ctx = Context(env_name, env_region, env_root)
            assert not ctx.command
            assert not ctx.debug
            assert ctx.env_name == env_name
            assert ctx.env_region == env_region
            assert ctx.env_root == env_root
            assert sorted(ctx.env_vars) == sorted(env_vars)

        with environ({'AWS_PROFILE': 'test', 'AWS_CONFIG_FILE': str(config_file)}):
            os.environ.pop('AWS_ACCESS_KEY_ID', None)
            os.environ.pop('AWS_SECRET_ACCESS_KEY', None)
            os.environ.pop('AWS_SESSION_TOKEN', None)

            env_vars = os.environ.copy()
            env_vars['DEPLOY_ENVIRONMENT'] = env_name

            ctx = Context(env_name, env_region, env_root)
            assert ctx.env_vars != os.environ
            assert ctx.env_vars['AWS_ACCESS_KEY_ID'] == 'bar'
            assert ctx.env_vars['AWS_SECRET_ACCESS_KEY'] == 'foo'
