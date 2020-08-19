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
            instance. (passed in by CFNgin)
        context (:class:`runway.cfngin.context.Context`): Context instance.
            (passed in by CFNgin)

    Keyword Args:
        domain (str): Domain name for the Route 53 hosted zone to be
            created.

    Returns:
        Dict[str, str]: Dict containing ``domain`` and ``zone_id``.

    """
    session = get_session(provider.region)
    client = session.client("route53")
    domain = kwargs.get("domain")
    if not domain:
        LOGGER.error("domain argument or BaseDomain variable required but not provided")
        return False
    zone_id = create_route53_zone(client, domain)
    return {"domain": domain, "zone_id": zone_id}
