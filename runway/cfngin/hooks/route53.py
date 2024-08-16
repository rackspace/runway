"""AWS Route 53 hook."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ...utils import BaseModel
from ..utils import create_route53_zone

if TYPE_CHECKING:
    from ...context import CfnginContext

LOGGER = logging.getLogger(__name__)


class CreateDomainHookArgs(BaseModel):
    """Hook arguments for ``create_domain``."""

    domain: str
    """Domain name for the Route 53 hosted zone to be created."""


def create_domain(context: CfnginContext, *_args: Any, **kwargs: Any) -> dict[str, str]:
    """Create a domain within route53.

    Args:
        context: CFNgin context object.
        **kwargs: Arbitrary keyword arguments.

    Returns:
        Dict containing ``domain`` and ``zone_id``.

    """
    args = CreateDomainHookArgs.model_validate(kwargs)
    client = context.get_session().client("route53")
    zone_id = create_route53_zone(client, args.domain)
    return {"domain": args.domain, "zone_id": zone_id}
