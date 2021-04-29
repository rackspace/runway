"""AWS Route 53 hook."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

from ..utils import create_route53_zone

if TYPE_CHECKING:
    from ...context import CfnginContext

LOGGER = logging.getLogger(__name__)


def create_domain(
    context: CfnginContext, *, domain: Optional[str] = None, **_: Any
) -> Dict[str, str]:
    """Create a domain within route53.

    Args:
        context: CFNgin context object.
        domain: Domain name for the Route 53 hosted zone to be created.

    Returns:
        Dict containing ``domain`` and ``zone_id``.

    """
    client = context.get_session().client("route53")
    if not domain:
        LOGGER.error("domain argument or BaseDomain variable required but not provided")
        return {}
    zone_id = create_route53_zone(client, domain)
    return {"domain": domain, "zone_id": zone_id}
