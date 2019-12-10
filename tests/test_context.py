"""Tests for context module."""
import logging
import sys
import unittest

from runway.context import Context


LOGGER = logging.getLogger('runway')


class ContextTester(unittest.TestCase):
    """Test Context class."""

    def test_init_name_from_arg(self):
        """_env_name_from_env should be false when DEPLOY_ENVIRONMENT not set"""
        context = Context(env_name='test', env_region='us-east-1',
                          env_root='./')
        self.assertEqual(context.env_name, 'test')
        self.assertEqual(context.env_vars['DEPLOY_ENVIRONMENT'],
                         context.env_name, 'env_vars.DEPLOY_ENVIRONMENT '
                         'should be set from env_name')
        self.assertFalse(context._env_name_from_env,
                         'should be false when env_name was not derived '
                         'from env_var')

    def test_init_from_envvar(self):
        """_env_name_from_env should be true when DEPLOY_ENVIRONMENT is set"""
        context = Context(env_name='test', env_region='us-east-1',
                          env_root='./', env_vars={'DEPLOY_ENVIRONMENT': 'test'})
        self.assertEqual(context.env_name, 'test')
        self.assertEqual(context.env_vars['DEPLOY_ENVIRONMENT'],
                         context.env_name, 'env_vars.DEPLOY_ENVIRONMENT '
                         'should be set from env_name')
        self.assertTrue(context._env_name_from_env,
                        'should be true when env_name was not derived '
                        'from env_var')

    def test_echo_detected_environment_not_env(self):
        """Environment helper note when DEPLOY_ENVIRONMENT is not set."""
        if sys.version_info[0] < 3:
            return  # this test method was not added until 3.4

        context = Context(env_name='test', env_region='us-east-1',
                          env_root='./')
        expected = ['INFO:runway:',
                    'INFO:runway:Environment "test" was determined from the '
                    'current git branch or parent directory.',
                    'INFO:runway:If this is not the environment name, update '
                    'the branch/folder name or set an override value via the '
                    'DEPLOY_ENVIRONMENT environment variable',
                    'INFO:runway:']

        with self.assertLogs(LOGGER, logging.INFO) as logs:
            context.echo_detected_environment()

        self.assertEqual(logs.output, expected)

    def test_echo_detected_environment_from_env(self):
        """Environment helper note when DEPLOY_ENVIRONMENT is set."""
        if sys.version_info[0] < 3:
            return  # this test method was not added until 3.4

        context = Context(env_name='test', env_region='us-east-1',
                          env_root='./', env_vars={'DEPLOY_ENVIRONMENT': 'test'})
        expected = ['INFO:runway:',
                    'INFO:runway:Environment "test" was determined from the '
                    'DEPLOY_ENVIRONMENT environment variable.',
                    'INFO:runway:If this is not correct, update the value (or '
                    'unset it to fall back to the name of the current git '
                    'branch or parent directory).',
                    'INFO:runway:']

        with self.assertLogs(LOGGER, logging.INFO) as logs:
            context.echo_detected_environment()

        self.assertEqual(logs.output, expected)

    def test_save_existing_iam_env_vars(self):
        """Test save_existing_iam_env_vars."""
        context = Context(env_name='dev', env_region='us-east-1',
                          env_root='./', env_vars={'AWS_ACCESS_KEY_ID': 'foo',
                                                   'AWS_SECRET_ACCESS_KEY': 'bar',  # noqa
                                                   'AWS_SESSION_TOKEN': 'foobar'})  # noqa
        context.save_existing_iam_env_vars()
        self.assertEqual(context.env_vars['OLD_AWS_ACCESS_KEY_ID'], 'foo')
        self.assertEqual(context.env_vars['OLD_AWS_SECRET_ACCESS_KEY'], 'bar')
        self.assertEqual(context.env_vars['OLD_AWS_SESSION_TOKEN'], 'foobar')
