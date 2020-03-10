"""Retrieve the ID of the Cognito User Pool."""
import logging

from typing import Any, Dict, Optional  # pylint: disable=unused-import

from runway.cfngin.providers.base import BaseProvider  # pylint: disable=unused-import
from runway.cfngin.context import Context  # noqa pylint: disable=unused-import

LOGGER = logging.getLogger(__name__)


def get(context,  # pylint: disable=unused-argument
        provider,  # pylint: disable=unused-argument
        **kwargs
       ):  # noqa: E124
    # type: (Context, BaseProvider, Optional[Dict[str, Any]]) -> Dict
    """Retrieve the ID of the Cognito User Pool.

    The User Pool can either be supplied via an ARN or by being generated.
    If the user has supplied an ARN that utilize that, otherwise retrieve
    the generated id. Used in multiple pre_hooks for Auth@Edge.

    Args:
        context (:class:`runway.cfngin.context.Context`): The context
            instance.
        provider (:class:`runway.cfngin.providers.base.BaseProvider`):
            The provider instance

    Keyword Args:
        user_pool_arn (str): The ARN of the supplied User pool
        created_user_pool_id (str): The ID of the created Cognito User Pool
    """
    context_dict = {'id': ''}

    # Favor a specific arn over a created one
    if kwargs['user_pool_arn']:
        context_dict['id'] = kwargs['user_pool_arn'].split('/')[-1:][0]
    elif kwargs['created_user_pool_id']:
        context_dict['id'] = kwargs['created_user_pool_id']

    return context_dict
