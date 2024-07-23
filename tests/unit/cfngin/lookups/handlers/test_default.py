"""Tests for runway.cfngin.lookups.handlers.default."""

import unittest
from unittest.mock import MagicMock

import pytest

from runway.cfngin.lookups.handlers.default import DefaultLookup
from runway.context import CfnginContext


class TestDefaultLookup(unittest.TestCase):
    """Tests for runway.cfngin.lookups.handlers.default.DefaultLookup."""

    def setUp(self) -> None:
        """Run before tests."""
        self.provider = MagicMock()
        self.context = CfnginContext(parameters={"namespace": "test", "env_var": "val_in_env"})

    def test_env_var_present(self) -> None:
        """Test env var present."""
        lookup_val = "env_var::fallback"
        value = DefaultLookup.handle(lookup_val, provider=self.provider, context=self.context)
        assert value == "val_in_env"

    def test_env_var_missing(self) -> None:
        """Test env var missing."""
        lookup_val = "bad_env_var::fallback"
        value = DefaultLookup.handle(lookup_val, provider=self.provider, context=self.context)
        assert value == "fallback"

    def test_invalid_value(self) -> None:
        """Test invalid value."""
        with pytest.raises(ValueError):  # noqa: PT011
            DefaultLookup.handle("env_var:fallback", provider=self.provider, context=self.context)
