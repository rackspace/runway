"""Tests for runway.cfngin.environment."""
import unittest

from runway.cfngin.environment import parse_environment

TEST_ENV = """key1: value1
# some: comment

 # here: about

# key2
key2: value2

# another comment here
key3: some:complex::value


# one more here as well
key4: :otherValue:
key5: <another>@value
"""

TEST_ERROR_ENV = """key1: value1
error
"""


class TestEnvironment(unittest.TestCase):
    """Tests for runway.cfngin.environment."""

    def test_simple_key_value_parsing(self):
        """Test simple key value parsing."""
        parsed_env = parse_environment(TEST_ENV)
        self.assertTrue(isinstance(parsed_env, dict))
        self.assertEqual(parsed_env["key1"], "value1")
        self.assertEqual(parsed_env["key2"], "value2")
        self.assertEqual(parsed_env["key3"], "some:complex::value")
        self.assertEqual(parsed_env["key4"], ":otherValue:")
        self.assertEqual(parsed_env["key5"], "<another>@value")
        self.assertEqual(len(parsed_env), 5)

    def test_simple_key_value_parsing_exception(self):
        """Test simple key value parsing exception."""
        with self.assertRaises(ValueError):
            parse_environment(TEST_ERROR_ENV)

    def test_blank_value(self):
        """Test blank value."""
        env = """key1:"""
        parsed = parse_environment(env)
        self.assertEqual(parsed["key1"], "")
