"""Test runway.cfngin.hooks.staticsite.auth_at_edge.user_pool_id_retriever."""

from __future__ import annotations

import pytest

from runway.cfngin.hooks.staticsite.auth_at_edge.user_pool_id_retriever import HookArgs

MODULE = "runway.cfngin.hooks.staticsite.auth_at_edge.user_pool_id_retriever"


@pytest.mark.parametrize(
    "provided, expected",
    [
        ({"user_pool_arn": "abc123"}, {"user_pool_arn": "abc123"}),
        ({"created_user_pool_id": "abc123"}, {"created_user_pool_id": "abc123"}),
        (
            {"created_user_pool_id": "abc123", "user_pool_arn": "abc123"},
            {"created_user_pool_id": "abc123", "user_pool_arn": "abc123"},
        ),
    ],
)
def test_hook_args_parse_obj(
    provided: dict[str, str], expected: dict[str, str]
) -> None:
    """Test HookArgs.parse_obj."""
    kwargs = provided
    args = HookArgs.parse_obj(kwargs)
    if "user_pool_arn" in provided:
        assert args.user_pool_arn == expected["user_pool_arn"]
    if "created_user_pool_id" in provided:
        assert args.created_user_pool_id == expected["created_user_pool_id"]
