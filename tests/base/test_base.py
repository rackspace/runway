"""Tests for context module."""
import unittest

from runway.commands.base import Base


class BaseTester(unittest.TestCase):
    """Test Base class."""

    def test_save_existing_iam_env_vars(self):
        """Test save_existing_iam_env_vars."""
        base = Base(options={},
                    env_vars={'AWS_ACCESS_KEY_ID': 'foo',
                              'AWS_SECRET_ACCESS_KEY': 'bar',
                              'AWS_SESSION_TOKEN': 'foobar'})
        base.save_existing_iam_env_vars()
        self.assertEqual(base.env_vars['OLD_AWS_ACCESS_KEY_ID'], 'foo')
        self.assertEqual(base.env_vars['OLD_AWS_SECRET_ACCESS_KEY'], 'bar')
        self.assertEqual(base.env_vars['OLD_AWS_SESSION_TOKEN'], 'foobar')
