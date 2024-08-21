"""Tests for lookup registry and common lookup functionality."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from runway.lookups.handlers.env import EnvLookup
from runway.lookups.registry import (
    RUNWAY_LOOKUP_HANDLERS,
    register_lookup_handler,
    unregister_lookup_handler,
)
from runway.utils import MutableMap

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from ..factories import MockRunwayContext

VALUES = {"str_val": "test"}
CONTEXT = MutableMap(env_vars=VALUES)
VARIABLES = MutableMap(**VALUES)


def test_autoloaded_lookup_handlers(mocker: MockerFixture) -> None:
    """Test autoloaded lookup handlers."""
    mocker.patch.dict(RUNWAY_LOOKUP_HANDLERS, {})
    handlers = ["cfn", "ecr", "env", "random.string", "ssm", "var"]
    for handler in handlers:
        assert handler in RUNWAY_LOOKUP_HANDLERS, f'Lookup handler: "{handler}" not registered'
    assert len(RUNWAY_LOOKUP_HANDLERS) == len(
        handlers
    ), f"expected {len(handlers)} autoloaded handlers but found {len(RUNWAY_LOOKUP_HANDLERS)}"


def test_register_lookup_handler_function() -> None:
    """Test register_lookup_handler function."""

    def fake_lookup(**_: Any) -> None:
        """Fake lookup."""

    with pytest.raises(TypeError):
        register_lookup_handler("test", fake_lookup)  # type: ignore


def test_register_lookup_handler_not_subclass() -> None:
    """Test register_lookup_handler no subclass."""

    class FakeLookup:
        """Fake lookup."""

    with pytest.raises(TypeError):
        register_lookup_handler("test", FakeLookup)  # type: ignore


def test_register_lookup_handler_str(mocker: MockerFixture) -> None:
    """Test register_lookup_handler from string."""
    mocker.patch.dict(RUNWAY_LOOKUP_HANDLERS, {})
    register_lookup_handler("test", "runway.lookups.handlers.env.EnvLookup")
    assert "test" in RUNWAY_LOOKUP_HANDLERS
    assert RUNWAY_LOOKUP_HANDLERS["test"] == EnvLookup


def test_unregister_lookup_handler(mocker: MockerFixture) -> None:
    """Test unregister_lookup_handler."""
    mocker.patch.dict(RUNWAY_LOOKUP_HANDLERS, {"test": "something"})
    assert "test" in RUNWAY_LOOKUP_HANDLERS
    unregister_lookup_handler("test")
    assert "test" not in RUNWAY_LOOKUP_HANDLERS


SUPPORTS_DEFAULT = ["env", "var"]


class TestCommonLookupFunctionality:
    """Test common lookup functionally.

    All lookup handles should be able to pass these tests. Handling must
    be implement in all lookups in the "handle" method using the provided
    class methods of the "LookupHandler" base class.

    """

    def test_handle_default(self, runway_context: MockRunwayContext) -> None:
        """Verify default value is handled by lookups."""
        lookup_handlers = RUNWAY_LOOKUP_HANDLERS.copy()
        for name, lookup in lookup_handlers.items():
            if name not in SUPPORTS_DEFAULT:
                continue
            result = lookup.handle(
                "NOT_VALID::default=default value",
                context=runway_context,
                variables=VARIABLES,
            )

            assert result == "default value"

    def test_handle_transform(self, runway_context: MockRunwayContext) -> None:
        """Verify transform is handled by lookup."""
        lookup_handlers = RUNWAY_LOOKUP_HANDLERS.copy()
        runway_context.env.vars.update(VALUES)

        for name, lookup in lookup_handlers.items():
            if name not in SUPPORTS_DEFAULT:
                continue
            result = lookup.handle(
                "NOT_VALID::default=false, transform=bool",
                context=runway_context,
                variables=VARIABLES,
            )

            assert not result
