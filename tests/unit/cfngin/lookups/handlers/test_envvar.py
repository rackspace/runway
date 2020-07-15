"""Tests for runway.cfngin.lookups.handlers.envvar."""
import os
import unittest

from runway.cfngin.lookups.handlers.envvar import EnvvarLookup


class TestEnvVarHandler(unittest.TestCase):
    """Tests for runway.cfngin.lookups.handlers.envvar.EnvvarLookup."""

    def setUp(self):
        """Run before tests."""
        self.testkey = 'STACKER_ENVVAR_TESTCASE'
        self.invalidtestkey = 'STACKER_INVALID_ENVVAR_TESTCASE'
        self.testval = 'TestVal'
        os.environ[self.testkey] = self.testval

    def test_valid_envvar(self):
        """Test valid envvar."""
        value = EnvvarLookup.handle(self.testkey)
        self.assertEqual(value, self.testval)

    def test_invalid_envvar(self):
        """Test invalid envvar."""
        with self.assertRaises(ValueError):
            EnvvarLookup.handle(self.invalidtestkey)
