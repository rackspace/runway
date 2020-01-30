"""AWS Route 53 hook."""
# pylint: disable=unused-argument
import logging

from ..session_cache import get_session
from ..util import create_route53_zone

LOGGER = logging.getLogger(__name__)


def create_domain(provider, context, **kwargs):
    """Create a domain within route53.

    Args:
        provider (:class:`runway.cfngin.providers.base.BaseProvider`): Provider
            instance.
        context (:class:`runway.cfngin.context.Context`): Context instance.

    Returns:
        Dict[str, str]

    """
    session = get_session(provider.region)
    client = session.client("route53")
    domain = kwargs.get("domain")
    if not domain:
        LOGGER.error("domain argument or BaseDomain variable not provided.")
        return False
    zone_id = create_route53_zone(client, domain)
    return {"domain": domain, "zone_id": zone_id}
