"""Helper functions for bootstrap actions."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from botocore.exceptions import ClientError

from runway.lookups.handlers.base import LookupHandler
from runway.utils import BaseModel

if TYPE_CHECKING:
    from runway.cfngin.providers.aws.default import Provider
    from runway.context import CfnginContext

TYPE_NAME = "bootstrap_value"


class HookArgs(BaseModel):
    """Hook arguments.

    Attributs:
        bootstrap: Value to return during bootstrap.
        post_bootstrap: Value to return post-bootstrap.

    """

    bootstrap: str
    post_bootstrap: str


class BootstrapValue(LookupHandler):
    """Return the bootstrap value on creation otherwise the post_bootstrap.

    .. rubric:: Example
    .. code-block:: yaml

        variables:
          variable: ${bootstrap_value <stack.name>::bootstrap=true, post_bootstrap=false}

    """

    # pylint: disable=arguments-differ
    @classmethod
    def handle(  # type: ignore
        cls,
        value: str,
        context: CfnginContext,
        *_args: Any,
        provider: Provider,
        **_kwargs: Any,
    ) -> str:
        """Handle lookup."""
        query, raw_args = cls.parse(value)
        args = HookArgs.parse_obj(raw_args)

        stack = context.get_stack(query)
        if not stack:
            raise ValueError(f"stack {query} not defined in CFNgin config")
        try:
            stack_des = provider.cloudformation.describe_stacks(StackName=stack.fqn)[
                "Stacks"
            ][0]
        except ClientError as exc:
            if "does not exist" not in str(exc):
                raise
            return args.bootstrap

        if provider.is_stack_completed(stack_des) or (
            provider.is_stack_in_progress(stack_des)
        ):
            return args.post_bootstrap
        return args.bootstrap
