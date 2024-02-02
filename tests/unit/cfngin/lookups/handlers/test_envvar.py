"""Tests for runway.cfngin.lookups.handlers.envvar."""

# pyright: basic
import os
import unittest

from runway.cfngin.lookups.handlers.envvar import EnvvarLookup


class TestEnvVarHandler(unittest.TestCase):
    """Tests for runway.cfngin.lookups.handlers.envvar.EnvvarLookup."""

    def setUp(self) -> None:
        """Run before tests."""
        self.testkey = "STACKER_ENVVAR_TESTCASE"
        self.invalidtestkey = "STACKER_INVALID_ENVVAR_TESTCASE"
        self.testval = "TestVal"
        os.environ[self.testkey] = self.testval

    def test_valid_envvar(self) -> None:
        """Test valid envvar."""
        value = EnvvarLookup.handle(self.testkey)
        self.assertEqual(value, self.testval)

    def test_invalid_envvar(self) -> None:
        """Test invalid envvar."""
        with self.assertRaises(ValueError):
            EnvvarLookup.handle(self.invalidtestkey)
