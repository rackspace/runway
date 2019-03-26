"""Tests for context module."""
import unittest

from runway.context import Context


class ContextTester(unittest.TestCase):
    """Test Context class."""

    def test_save_existing_iam_env_vars(self):
        """Test save_existing_iam_env_vars."""
        context = Context(options={}, env_name='dev', env_region='us-east-1',
                          env_root='./', env_vars={'AWS_ACCESS_KEY_ID': 'foo',
                                                   'AWS_SECRET_ACCESS_KEY': 'bar',  # noqa
                                                   'AWS_SESSION_TOKEN': 'foobar'})  # noqa
        context.save_existing_iam_env_vars()
        self.assertEqual(context.env_vars['OLD_AWS_ACCESS_KEY_ID'], 'foo')
        self.assertEqual(context.env_vars['OLD_AWS_SECRET_ACCESS_KEY'], 'bar')
        self.assertEqual(context.env_vars['OLD_AWS_SESSION_TOKEN'], 'foobar')
