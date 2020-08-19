"""Tests for runway.cfngin.lookups.registry."""
# pylint: disable=no-self-use
import unittest

from mock import MagicMock

from runway.cfngin.exceptions import FailedVariableLookup, UnknownLookupType
from runway.cfngin.lookups.registry import CFNGIN_LOOKUP_HANDLERS
from runway.variables import Variable, VariableValueLookup

from ..factories import mock_context, mock_provider


class TestRegistry(unittest.TestCase):
    """Tests for runway.cfngin.lookups.registry."""

    def setUp(self):
        """Run before tests."""
        self.ctx = mock_context()
        self.provider = mock_provider()

    def test_autoloaded_lookup_handlers(self):
        """Test autoloaded lookup handlers."""
        handlers = [
            "output",
            "xref",
            "kms",
            "ssm",
            "ssmstore",
            "envvar",
            "rxref",
            "ami",
            "file",
            "split",
            "default",
            "hook_data",
            "dynamodb",
        ]
        for handler in handlers:
            try:
                CFNGIN_LOOKUP_HANDLERS[handler]
            except KeyError:
                assert False, 'Lookup handler: "{}" was not registered'.format(handler)

    def test_resolve_lookups_string_unknown_lookup(self):
        """Test resolve lookups string unknown lookup."""
        with self.assertRaises(UnknownLookupType):
            Variable("MyVar", "${bad_lookup foo}")

    def test_resolve_lookups_list_unknown_lookup(self):
        """Test resolve lookups list unknown lookup."""
        with self.assertRaises(UnknownLookupType):
            Variable("MyVar", ["${bad_lookup foo}", "random string"])

    def resolve_lookups_with_output_handler_raise_valueerror(self, variable):
        """Resolve lookups with output handler raise valueerror.

        Mock output handler to throw ValueError, then run resolve_lookups
        on the given variable.

        """
        mock_handler = MagicMock(side_effect=ValueError("Error"))

        # find the only lookup in the variable
        for value in variable._value:  # pylint: disable=protected-access
            if isinstance(value, VariableValueLookup):
                value.handler = mock_handler

        with self.assertRaises(FailedVariableLookup) as result:
            variable.resolve(self.ctx, self.provider)

        self.assertIsInstance(result.exception.error, ValueError)

    def test_resolve_lookups_string_failed_variable_lookup(self):
        """Test resolve lookups string failed variable lookup."""
        variable = Variable("MyVar", "${output foo::bar}")
        self.resolve_lookups_with_output_handler_raise_valueerror(variable)

    def test_resolve_lookups_list_failed_variable_lookup(self):
        """Test resolve lookups list failed variable lookup."""
        variable = Variable(
            "MyVar", ["random string", "${output foo::bar}", "random string"]
        )
        self.resolve_lookups_with_output_handler_raise_valueerror(variable)
