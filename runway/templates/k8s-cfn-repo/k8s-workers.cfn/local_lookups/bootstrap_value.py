#!/usr/bin/env python
"""Helper functions for bootstrap actions."""

import botocore


def bootstrap_value(value, context, **kwargs):
    """Return the bootstrap value on creation, otherwise the post_bootstrap.

    Format of value:
        <stack>::<bootstrap value>::<post_bootstrap_value>
    """
    try:
        stack_name, bootstrap_val, post_bootstrap_val = value.split("::")
    except ValueError:
        raise ValueError(
            "Invalid value for bootstrap_value lookup: %s. Must "
            "be in <stack>::<bootstrap value>::"
            "<post_bootstrap val> format." % value
        )

    stack = next(i for i in context.get_stacks() if i.name == stack_name)
    try:
        stack_des = kwargs["provider"].cloudformation.describe_stacks(
            StackName=stack.fqn
        )["Stacks"][0]
    except botocore.exceptions.ClientError as exc:
        if "does not exist" not in str(exc):
            raise
        return bootstrap_val

    if kwargs["provider"].is_stack_completed(stack_des) or (
        kwargs["provider"].is_stack_in_progress(stack_des)
    ):
        return post_bootstrap_val
    return bootstrap_val
