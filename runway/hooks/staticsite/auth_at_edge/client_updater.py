"""User Pool Client Updater.

Responsible for updating the User Pool Client with the generated
distribution url + callback url paths.
"""

import logging
from typing import Any, Dict, Optional  # pylint: disable=unused-import

from runway.cfngin.providers.base import BaseProvider  # pylint: disable=unused-import
from runway.cfngin.context import Context  # noqa pylint: disable=unused-import
from runway.cfngin.session_cache import get_session

LOGGER = logging.getLogger(__name__)


def update(context,  # pylint: disable=unused-argument
           provider,
           **kwargs
          ):  # noqa: E124
    # type: (Context, BaseProvider, Optional[Dict[str, Any]]) -> bool
    """Update the callback urls for the User Pool Client.

    Required to match the redirect_uri being sent which contains
    our distribution and alternate domain names.

    Args:
        context (:class:`runway.cfngin.context.Context`): The context
            instance.
        provider (:class:`runway.cfngin.providers.base.BaseProvider`):
            The provider instance

    Keyword Args:
        alternate_domains (List[str]): A list of any alternate domains
            that need to be listed with the primary distribution domain
        redirect_path_sign_in (str): The redirect path after sign in
        redirect_path_sign_out (str): The redirect path after sign out
        oauth_scopes (List[str]): A list of all available validation
            scopes for oauth
    """
    session = get_session(provider.region)
    cognito_client = session.client('cognito-idp')

    # Combine alternate domains with main distribution
    redirect_domains = kwargs['alternate_domains'] + ['https://' + kwargs['distribution_domain']]

    # Create a list of all domains with their redirect paths
    redirect_uris_sign_in = [
        "%s%s" % (domain, kwargs['redirect_path_sign_in'])
        for domain in redirect_domains
    ]
    redirect_uris_sign_out = [
        "%s%s" % (domain, kwargs['redirect_path_sign_out'])
        for domain in redirect_domains
    ]
    # Update the user pool client
    try:
        cognito_client.update_user_pool_client(
            AllowedOAuthScopes=kwargs['oauth_scopes'],
            AllowedOAuthFlows=['code'],
            SupportedIdentityProviders=kwargs['supported_identity_providers'],
            AllowedOAuthFlowsUserPoolClient=True,
            ClientId=kwargs['client_id'],
            CallbackURLs=redirect_uris_sign_in,
            LogoutURLs=redirect_uris_sign_out,
            UserPoolId=context.hook_data['aae_user_pool_id_retriever']['id'],
        )
        return True
    except Exception as err:  # pylint: disable=broad-except
        LOGGER.error('Was not able to update the callback urls on '
                     'the user pool client')
        LOGGER.error(err)
        return False
