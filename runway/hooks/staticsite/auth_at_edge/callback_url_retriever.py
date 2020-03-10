"""Callback URL Retriever.

Dependency pre-hook responsible for ensuring correct
callback urls are retrieved or a temporary one is used in it's place.
"""

import logging

from typing import Any, Dict, Optional  # pylint: disable=unused-import

from runway.cfngin.providers.base import BaseProvider  # pylint: disable=unused-import
from runway.cfngin.context import Context  # noqa pylint: disable=unused-import
from runway.cfngin.session_cache import get_session

LOGGER = logging.getLogger(__name__)


def get(context,  # pylint: disable=unused-argument
        provider,
        **kwargs
       ):  # noqa: E124
    # type: (Context, BaseProvider, Optional[Dict[str, Any]]) -> Dict
    """Retrieve the callback URLs for User Pool Client Creation.

    When the User Pool is created a Callback URL is required. During a post
    hook entitled ``client_updater`` these Callback URLs are updated to that
    of the Distribution. Before then we need to ensure that if a Client
    already exists that the URLs for that client are used to prevent any
    interuption of service during deploy.

    Args:
        context (:class:`runway.cfngin.context.Context`): The context
            instance.
        provider (:class:`runway.cfngin.providers.base.BaseProvider`):
            The provider instance

    Keyword Args:
        user_pool_id (str): The ID of the User Pool to check for a client
    """
    session = get_session(provider.region)
    cognito_client = session.client('cognito-idp')
    context_dict = {}
    context_dict['callback_urls'] = ['https://example.tmp']

    try:
        clients = cognito_client.list_user_pool_clients(
            UserPoolId=kwargs['user_pool_id']
        )['UserPoolClients']

        client = next((c for c in clients if c['ClientName'].startswith('AuthAtEdge')), None)

        resp = cognito_client.describe_user_pool_client(
            UserPoolId=kwargs['user_pool_id'],
            ClientId=client['ClientId']
        )

        callbacks = resp['UserPoolClient']['CallbackURLs']

        if callbacks:
            context_dict['callback_urls'] = callbacks
        return context_dict
    except Exception:  # pylint: disable=broad-except
        return context_dict
