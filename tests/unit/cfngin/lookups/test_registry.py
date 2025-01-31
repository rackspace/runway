"""Tests for runway.cfngin.lookups.registry."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from runway.cfngin.lookups.handlers.default import DefaultLookup
from runway.cfngin.lookups.registry import (
    CFNGIN_LOOKUP_HANDLERS,
    register_lookup_handler,
    unregister_lookup_handler,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_autoloaded_lookup_handlers(mocker: MockerFixture) -> None:
    """Test autoloaded lookup handlers."""
    mocker.patch.dict(CFNGIN_LOOKUP_HANDLERS, {})
    handlers = [
        "ami",
        "awslambda",
        "awslambda.Code",
        "awslambda.CodeSha256",
        "awslambda.CompatibleArchitectures",
        "awslambda.CompatibleRuntimes",
        "awslambda.Content",
        "awslambda.LicenseInfo",
        "awslambda.Runtime",
        "awslambda.S3Bucket",
        "awslambda.S3Key",
        "awslambda.S3ObjectVersion",
        "cfn",
        "default",
        "dynamodb",
        "ecr",
        "env",
        "envvar",
        "file",
        "hook_data",
        "kms",
        "output",
        "random.string",
        "rxref",
        "split",
        "ssm",
        "xref",
    ]
    for handler in handlers:
        assert handler in CFNGIN_LOOKUP_HANDLERS, f'Lookup handler: "{handler}" not registered'
    assert len(CFNGIN_LOOKUP_HANDLERS) == len(handlers), (
        f"expected {len(handlers)} autoloaded handlers but found {len(CFNGIN_LOOKUP_HANDLERS)}"
    )


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
    mocker.patch.dict(CFNGIN_LOOKUP_HANDLERS, {})
    register_lookup_handler("test", "runway.cfngin.lookups.handlers.default.DefaultLookup")
    assert "test" in CFNGIN_LOOKUP_HANDLERS
    assert CFNGIN_LOOKUP_HANDLERS["test"] == DefaultLookup


def test_unregister_lookup_handler(mocker: MockerFixture) -> None:
    """Test unregister_lookup_handler."""
    mocker.patch.dict(CFNGIN_LOOKUP_HANDLERS, {"test": "something"})
    assert "test" in CFNGIN_LOOKUP_HANDLERS
    unregister_lookup_handler("test")
    assert "test" not in CFNGIN_LOOKUP_HANDLERS
