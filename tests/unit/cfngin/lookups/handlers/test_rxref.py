"""Tests for runway.cfngin.lookups.handlers.rxref."""
# pyright: basic, reportUnknownArgumentType=none, reportUnknownVariableType=none
import unittest

from mock import MagicMock

from runway.cfngin.lookups.handlers.rxref import RxrefLookup
from runway.config import CfnginConfig
from runway.context import CfnginContext


class TestRxrefHandler(unittest.TestCase):
    """Tests for runway.cfngin.lookups.handlers.rxref.RxrefLookup."""

    def setUp(self) -> None:
        """Run before tests."""
        self.provider = MagicMock()
        self.context = CfnginContext(config=CfnginConfig.parse_obj({"namespace": "ns"}))

    def test_rxref_handler(self) -> None:
        """Test rxref handler."""
        self.provider.get_output.return_value = "Test Output"

        value = RxrefLookup.handle(
            "fully-qualified-stack-name::SomeOutput",
            provider=self.provider,
            context=self.context,
        )
        self.assertEqual(value, "Test Output")

        args = self.provider.get_output.call_args
        self.assertEqual(args[0][0], "ns-fully-qualified-stack-name")
        self.assertEqual(args[0][1], "SomeOutput")
