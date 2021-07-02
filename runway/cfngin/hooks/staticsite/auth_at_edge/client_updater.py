"""User Pool Client Updater.

Responsible for updating the User Pool Client with the generated
distribution url + callback url paths.

"""
# pylint: disable=unused-argument
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .....context import CfnginContext

LOGGER = logging.getLogger(__name__)


def get_redirect_uris(
    domains: List[str], redirect_path_sign_in: str, redirect_path_sign_out: str
) -> Dict[str, List[str]]:
    """Create dict of redirect URIs for AppClient."""
    return {
        "sign_in": [f"{domain}{redirect_path_sign_in}" for domain in domains],
        "sign_out": [f"{domain}{redirect_path_sign_out}" for domain in domains],
    }


def update(
    context: CfnginContext,
    *,
    alternate_domains: List[str],
    client_id: str,
    distribution_domain: str,
    oauth_scopes: List[str],
    redirect_path_sign_in: str,
    redirect_path_sign_out: str,
    supported_identity_providers: Optional[List[str]] = None,
    **_: Any,
) -> bool:
    """Update the callback urls for the User Pool Client.

    Required to match the redirect_uri being sent which contains
    our distribution and alternate domain names.

    Args:
        context: The context instance.
        alternate_domains: A list of any alternate domains
            that need to be listed with the primary distribution domain.
        client_id: CLient ID.
        distribution_domain: Distribution domain.
        oauth_scopes: A list of all available validation
            scopes for oauth.
        redirect_path_sign_in: The redirect path after sign in.
        redirect_path_sign_out: The redirect path after sign out.
        supported_identity_providers: Supported identity providers.

    """
    session = context.get_session()
    cognito_client = session.client("cognito-idp")

    # Combine alternate domains with main distribution
    redirect_domains = alternate_domains + ["https://" + distribution_domain]

    # Create a list of all domains with their redirect paths
    redirect_uris = get_redirect_uris(
        redirect_domains, redirect_path_sign_in, redirect_path_sign_out
    )
    # Update the user pool client
    try:
        cognito_client.update_user_pool_client(
            AllowedOAuthScopes=oauth_scopes,
            AllowedOAuthFlows=["code"],
            SupportedIdentityProviders=supported_identity_providers,
            AllowedOAuthFlowsUserPoolClient=True,
            ClientId=client_id,
            CallbackURLs=redirect_uris["sign_in"],
            LogoutURLs=redirect_uris["sign_out"],
            UserPoolId=context.hook_data["aae_user_pool_id_retriever"]["id"],
        )
        return True
    except Exception:  # pylint: disable=broad-except
        LOGGER.exception("unable to update user pool client callback urls")
        return False
