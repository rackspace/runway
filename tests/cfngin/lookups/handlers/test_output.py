"""Tests for runway.cfngin.lookups.handlers.output."""
import unittest

from mock import MagicMock

from runway.cfngin.lookups.handlers.output import OutputLookup
from runway.cfngin.stack import Stack

from ...factories import generate_definition


class TestOutputHandler(unittest.TestCase):
    """Tests for runway.cfngin.lookups.handlers.output.OutputLookup."""

    def setUp(self):
        """Run before tests."""
        self.context = MagicMock()

    def test_output_handler(self):
        """Test output handler."""
        stack = Stack(
            definition=generate_definition("vpc", 1),
            context=self.context)
        stack.set_outputs({
            "SomeOutput": "Test Output"})
        self.context.get_stack.return_value = stack
        value = OutputLookup.handle("stack-name::SomeOutput",
                                    context=self.context)
        self.assertEqual(value, "Test Output")
        self.assertEqual(self.context.get_stack.call_count, 1)
        args = self.context.get_stack.call_args
        self.assertEqual(args[0][0], "stack-name")
