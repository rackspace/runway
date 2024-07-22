"""Tests for runway.cfngin.hooks.cleanup_ssm."""

from __future__ import annotations

from typing import TYPE_CHECKING

from runway.cfngin.hooks.cleanup_ssm import delete_param

if TYPE_CHECKING:
    from ...factories import MockCfnginContext


def test_delete_param(cfngin_context: MockCfnginContext) -> None:
    """Test delete_param."""
    stub = cfngin_context.add_stubber("ssm")

    stub.add_response("delete_parameter", {}, {"Name": "foo"})
    with stub:
        assert delete_param(cfngin_context, parameter_name="foo")


def test_delete_param_not_found(cfngin_context: MockCfnginContext) -> None:
    """Test delete_param."""
    stub = cfngin_context.add_stubber("ssm")

    stub.add_client_error("delete_parameter", "ParameterNotFound")
    with stub:
        assert delete_param(cfngin_context, parameter_name="foo")
