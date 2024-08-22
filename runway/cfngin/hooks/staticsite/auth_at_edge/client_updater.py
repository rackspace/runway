"""User Pool Client Updater.

Responsible for updating the User Pool Client with the generated
distribution url + callback url paths.

"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ...base import HookArgsBaseModel

if TYPE_CHECKING:
    from .....context import CfnginContext

LOGGER = logging.getLogger(__name__)


class HookArgs(HookArgsBaseModel):
    """Hook arguments."""

    alternate_domains: list[str]
    """A list of any alternate domains that need to be listed with the primary
    distribution domain.

    """

    client_id: str
    """Client ID."""

    distribution_domain: str
    """Distribution domain."""

    oauth_scopes: list[str]
    """A list of all available validation scopes for oauth."""

    redirect_path_sign_in: str
    """The redirect path after sign in."""

    redirect_path_sign_out: str
    """The redirect path after sign out."""

    supported_identity_providers: list[str] = []
    """Supported identity providers."""


def get_redirect_uris(
    domains: list[str], redirect_path_sign_in: str, redirect_path_sign_out: str
) -> dict[str, list[str]]:
    """Create dict of redirect URIs for AppClient."""
    return {
        "sign_in": [f"{domain}{redirect_path_sign_in}" for domain in domains],
        "sign_out": [f"{domain}{redirect_path_sign_out}" for domain in domains],
    }


def update(context: CfnginContext, *_args: Any, **kwargs: Any) -> bool:
    """Update the callback urls for the User Pool Client.

    Required to match the redirect_uri being sent which contains
    our distribution and alternate domain names.

    Arguments parsed by
    :class:`~runway.cfngin.hooks.staticsite.auth_at_edge.client_updater.HookArgs`.

    Args:
        context: The context instance.
        **kwargs: Arbitrary keyword arguments.

    """
    args = HookArgs.model_validate(kwargs)
    session = context.get_session()
    cognito_client = session.client("cognito-idp")

    # Combine alternate domains with main distribution
    redirect_domains = [*args.alternate_domains, "https://" + args.distribution_domain]

    # Create a list of all domains with their redirect paths
    redirect_uris = get_redirect_uris(
        redirect_domains, args.redirect_path_sign_in, args.redirect_path_sign_out
    )
    # Update the user pool client
    try:
        cognito_client.update_user_pool_client(
            AllowedOAuthScopes=args.oauth_scopes,
            AllowedOAuthFlows=["code"],
            SupportedIdentityProviders=args.supported_identity_providers,
            AllowedOAuthFlowsUserPoolClient=True,
            ClientId=args.client_id,
            CallbackURLs=redirect_uris["sign_in"],
            LogoutURLs=redirect_uris["sign_out"],
            UserPoolId=context.hook_data["aae_user_pool_id_retriever"]["id"],
        )
        return True
    except Exception:
        LOGGER.exception("unable to update user pool client callback urls")
        return False
