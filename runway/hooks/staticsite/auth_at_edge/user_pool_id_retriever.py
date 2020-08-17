"""Retrieve the ID of the Cognito User Pool."""
# pylint: disable=unused-argument
import logging
from typing import TYPE_CHECKING, Any, Dict, Optional  # noqa pylint: disable=W

if TYPE_CHECKING:
    from ....cfngin.context import Context  # pylint: disable=W
    from ....cfngin.providers.base import BaseProvider  # pylint: disable=W

LOGGER = logging.getLogger(__name__)


def get(context, provider, **kwargs):
    # type: (Context, BaseProvider, Optional[Dict[str, Any]]) -> Dict
    """Retrieve the ID of the Cognito User Pool.

    The User Pool can either be supplied via an ARN or by being generated.
    If the user has supplied an ARN that utilize that, otherwise retrieve
    the generated id. Used in multiple pre_hooks for Auth@Edge.

    Args:
        context (:class:`runway.cfngin.context.Context`): The context
            instance.
        provider (:class:`runway.cfngin.providers.base.BaseProvider`):
            The provider instance.

    Keyword Args:
        user_pool_arn (str): The ARN of the supplied User pool.
        created_user_pool_id (str): The ID of the created Cognito User Pool.

    """
    context_dict = {"id": ""}

    # Favor a specific arn over a created one
    if kwargs["user_pool_arn"]:
        context_dict["id"] = kwargs["user_pool_arn"].split("/")[-1:][0]
    elif kwargs["created_user_pool_id"]:
        context_dict["id"] = kwargs["created_user_pool_id"]

    return context_dict
