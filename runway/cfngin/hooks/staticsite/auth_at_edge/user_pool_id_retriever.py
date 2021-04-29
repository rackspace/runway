"""Retrieve the ID of the Cognito User Pool."""
import logging
from typing import Any, Dict, Optional

LOGGER = logging.getLogger(__name__)


def get(
    *,
    created_user_pool_id: Optional[str] = None,
    user_pool_arn: Optional[str] = None,
    **_: Any,
) -> Dict[str, Any]:
    """Retrieve the ID of the Cognito User Pool.

    The User Pool can either be supplied via an ARN or by being generated.
    If the user has supplied an ARN that utilize that, otherwise retrieve
    the generated id. Used in multiple pre_hooks for Auth@Edge.

    Args:
        user_pool_arn: The ARN of the supplied User pool.
        created_user_pool_id: The ID of the created Cognito User Pool.

    """
    context_dict = {"id": ""}

    # Favor a specific arn over a created one
    if user_pool_arn:
        context_dict["id"] = user_pool_arn.split("/")[-1:][0]
    elif created_user_pool_id:
        context_dict["id"] = created_user_pool_id

    return context_dict
