#!/usr/bin/env python
"""Helper functions for bootstrap actions."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from botocore.exceptions import ClientError

if TYPE_CHECKING:
    from runway.context import CfnginContext


def bootstrap_value(value: str, context: CfnginContext, **kwargs: Any) -> str:
    """Return the bootstrap value on creation, otherwise the post_bootstrap.

    Format of value:
        <stack>::<bootstrap value>::<post_bootstrap_value>
    """
    try:
        stack_name, bootstrap_val, post_bootstrap_val = value.split("::")
    except ValueError:
        raise ValueError(
            f"Invalid value for bootstrap_value lookup: {value}. Must "
            "be in <stack>::<bootstrap value>::"
            "<post_bootstrap val> format."
        )

    stack = next(i for i in context.stacks_dict.values() if i.name == stack_name)
    try:
        stack_des = kwargs["provider"].cloudformation.describe_stacks(
            StackName=stack.fqn
        )["Stacks"][0]
    except ClientError as exc:
        if "does not exist" not in str(exc):
            raise
        return bootstrap_val

    if kwargs["provider"].is_stack_completed(stack_des) or (
        kwargs["provider"].is_stack_in_progress(stack_des)
    ):
        return post_bootstrap_val
    return bootstrap_val
