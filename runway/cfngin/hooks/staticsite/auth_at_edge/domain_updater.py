"""User Pool Client Domain Updater."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, Union

if TYPE_CHECKING:
    from .....context import CfnginContext

LOGGER = logging.getLogger(__name__)


def update(
    context: CfnginContext, *, client_id: str, **_: Any
) -> Union[Dict[str, Any], bool]:
    """Retrieve/Update the domain name of the specified client.

    A domain name is required in order to make authorization and token
    requests. This prehook ensures we have one available, and if not
    we create one based on the user pool and client ids.

    Args:
        context: The context instance.
        client_id: The ID of the Cognito User Pool Client.

    """
    session = context.get_session()
    cognito_client = session.client("cognito-idp")

    context_dict: Dict[str, Any] = {}

    user_pool_id = context.hook_data["aae_user_pool_id_retriever"]["id"]
    user_pool = cognito_client.describe_user_pool(UserPoolId=user_pool_id).get(
        "UserPool", {}
    )
    (user_pool_region, user_pool_hash) = user_pool_id.split("_")

    domain_prefix = user_pool.get("CustomDomain", user_pool.get("Domain"))

    # Return early if we already have a domain
    if domain_prefix:
        context_dict["domain"] = get_user_pool_domain(domain_prefix, user_pool_region)
        return context_dict

    try:
        domain_prefix = (f"{user_pool_hash}-{client_id}").lower()

        cognito_client.create_user_pool_domain(
            Domain=domain_prefix, UserPoolId=user_pool_id
        )
        context_dict["domain"] = get_user_pool_domain(domain_prefix, user_pool_region)
        return context_dict
    except Exception:  # pylint: disable=broad-except
        LOGGER.exception("could not update user pool domain: %s", user_pool_id)
        return False


def delete(
    context: CfnginContext, *, client_id: str, **_: Any
) -> Union[Dict[str, Any], bool]:
    """Delete the domain if the user pool was created by Runway.

    If a User Pool was created by Runway, and populated with a domain, that
    domain must be deleted prior to the User Pool itself being deleted or an
    error will occur. This process ensures that our generated domain name is
    deleted, or skips if not able to find one.

    Args:
        context: The context instance.
        client_id: The ID of the Cognito User Pool Client.

    """
    session = context.get_session()
    cognito_client = session.client("cognito-idp")

    user_pool_id = context.hook_data["aae_user_pool_id_retriever"]["id"]
    _, user_pool_hash = user_pool_id.split("_")
    domain_prefix = (f"{user_pool_hash}-{client_id}").lower()

    try:
        cognito_client.delete_user_pool_domain(
            UserPoolId=user_pool_id, Domain=domain_prefix
        )
        return True
    except cognito_client.exceptions.InvalidParameterException:
        LOGGER.info('skipped deletion; no domain with prefix "%s"', domain_prefix)
        return True
    except Exception:  # pylint: disable=broad-except
        LOGGER.exception("could not delete user pool domain")
        return False


def get_user_pool_domain(prefix: str, region: str) -> str:
    """Return a user pool domain name based on the prefix received and region.

    Args:
        prefix: The domain prefix for the domain.
        region: The region in which the pool resides.

    """
    return f"{prefix}.auth.{region}.amazoncognito.com"
