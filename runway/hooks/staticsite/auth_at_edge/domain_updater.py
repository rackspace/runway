"""User Pool Client Domain Updater."""
# pylint: disable=unused-argument
import logging
from typing import (  # pylint: disable=unused-import
    TYPE_CHECKING,
    Any,
    Dict,
    Optional,
    Union,
)

if TYPE_CHECKING:
    from ....cfngin.context import Context  # pylint: disable=W
    from ....cfngin.providers.base import BaseProvider  # pylint: disable=W

LOGGER = logging.getLogger(__name__)


def update(
    context,  # type: Context
    provider,  # type: BaseProvider
    **kwargs  # type: Optional[Dict[str, Any]]
):
    # type: (...) -> Union[Dict[str, Any], bool]
    """Retrieve/Update the domain name of the specified client.

    A domain name is required in order to make authorization and token
    requests. This prehook ensures we have one available, and if not
    we create one based on the user pool and client ids.

    Args:
        context (:class:`runway.cfngin.context.Context`): The context
            instance.
        provider (:class:`runway.cfngin.providers.base.BaseProvider`):
            The provider instance.

    Keyword Args:
        user_pool_id (str): The ID of the Cognito User Pool.
        client_id (str): The ID of the Cognito User Pool Client.

    """
    session = context.get_session()
    cognito_client = session.client("cognito-idp")

    context_dict = {}

    user_pool_id = context.hook_data["aae_user_pool_id_retriever"]["id"]
    client_id = kwargs["client_id"]
    user_pool = cognito_client.describe_user_pool(UserPoolId=user_pool_id).get(
        "UserPool"
    )
    (user_pool_region, user_pool_hash) = user_pool_id.split("_")

    domain_prefix = user_pool.get("CustomDomain") or user_pool.get("Domain")

    # Return early if we already have a domain
    if domain_prefix:
        context_dict["domain"] = get_user_pool_domain(domain_prefix, user_pool_region)
        return context_dict

    try:
        domain_prefix = ("%s-%s" % (user_pool_hash, client_id)).lower()

        cognito_client.create_user_pool_domain(
            Domain=domain_prefix, UserPoolId=user_pool_id
        )
        context_dict["domain"] = get_user_pool_domain(domain_prefix, user_pool_region)
        return context_dict
    except Exception:  # pylint: disable=broad-except
        LOGGER.exception("could not update user pool domain: %s", user_pool_id)
        return False


def delete(
    context,  # type: Context
    provider,  # type: BaseProvider
    **kwargs  # type: Optional[Dict[str, Any]]
):
    # type: (...) -> Union[Dict[str, Any], bool]
    """Delete the domain if the user pool was created by Runway.

    If a User Pool was created by Runway, and populated with a domain, that
    domain must be deleted prior to the User Pool itself being deleted or an
    error will occur. This process ensures that our generated domain name is
    deleted, or skips if not able to find one.

    Args:
        context (:class:`runway.cfngin.context.Context`): The context
            instance.
        provider (:class:`runway.cfngin.providers.base.BaseProvider`):
            The provider instance.

    Keyword Args:
        client_id (str): The ID of the Cognito User Pool Client.

    """
    session = context.get_session()
    cognito_client = session.client("cognito-idp")

    user_pool_id = context.hook_data["aae_user_pool_id_retriever"]["id"]
    client_id = kwargs["client_id"]
    (_, user_pool_hash) = user_pool_id.split("_")
    domain_prefix = ("%s-%s" % (user_pool_hash, client_id)).lower()

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


def get_user_pool_domain(prefix, region):
    """Return a user pool domain name based on the prefix received and region.

    Args:
        prefix (str): The domain prefix for the domain.
        region (str): The region in which the pool resides.

    """
    return "%s.auth.%s.amazoncognito.com" % (prefix, region)
