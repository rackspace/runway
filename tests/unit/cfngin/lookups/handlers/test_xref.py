"""Tests for runway.cfngin.lookups.handlers.xref."""

# pyright: reportUnknownArgumentType=none, reportUnknownVariableType=none
import unittest
from unittest.mock import MagicMock

from runway.cfngin.lookups.handlers.xref import XrefLookup


class TestXrefHandler(unittest.TestCase):
    """Tests for runway.cfngin.lookups.handlers.xref.XrefHandler."""

    def setUp(self) -> None:
        """Run before tests."""
        self.provider = MagicMock()
        self.context = MagicMock()

    def test_xref_handler(self) -> None:
        """Test xref handler."""
        self.provider.get_output.return_value = "Test Output"
        value = XrefLookup.handle(
            "fully-qualified-stack-name::SomeOutput",
            provider=self.provider,
            context=self.context,
        )
        assert value == "Test Output"
        assert self.context.get_fqn.call_count == 0
        args = self.provider.get_output.call_args
        assert args[0][0] == "fully-qualified-stack-name"
        assert args[0][1] == "SomeOutput"
