"""Retrieve the ID of the Cognito User Pool."""
import logging
from typing import Any, Dict

from ...base import HookArgsBaseModel

LOGGER = logging.getLogger(__name__)


class HookArgs(HookArgsBaseModel):
    """Hook arguments."""

    created_user_pool_id: str
    """The ID of the created Cognito User Pool."""

    user_pool_arn: str
    """The ARN of the supplied User pool."""


def get(*__args: Any, **kwargs: Any) -> Dict[str, Any]:
    """Retrieve the ID of the Cognito User Pool.

    The User Pool can either be supplied via an ARN or by being generated.
    If the user has supplied an ARN that utilize that, otherwise retrieve
    the generated id. Used in multiple pre_hooks for Auth@Edge.

    Arguments parsed by
    :class:`~runway.cfngin.hooks.staticsite.auth_at_edge.user_pool_id_retriever.HookArgs`.

    """
    args = HookArgs.parse_obj(kwargs)

    # Favor a specific arn over a created one
    if args.user_pool_arn:
        return {"id": args.user_pool_arn.split("/")[-1:][0]}
    if args.created_user_pool_id:
        return {"id": args.created_user_pool_id}
    return {"id": ""}
