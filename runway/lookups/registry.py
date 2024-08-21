"""Register test handlers."""

from __future__ import annotations

import logging
from typing import Any, cast

from ..utils import load_object_from_string
from .handlers.base import LookupHandler
from .handlers.cfn import CfnLookup
from .handlers.ecr import EcrLookup
from .handlers.env import EnvLookup
from .handlers.random_string import RandomStringLookup
from .handlers.ssm import SsmLookup
from .handlers.var import VarLookup

RUNWAY_LOOKUP_HANDLERS: dict[str, type[LookupHandler[Any]]] = {}
LOGGER = logging.getLogger(__name__)


def register_lookup_handler(
    lookup_type: str, handler_or_path: str | type[LookupHandler[Any]]
) -> None:
    """Register a lookup handler.

    Args:
        lookup_type: Name to register the handler under
        handler_or_path: a function or a path to a handler

    """
    handler = handler_or_path

    if isinstance(handler_or_path, str):
        handler = cast(type, load_object_from_string(handler_or_path))
    else:
        handler = handler_or_path

    try:
        if issubclass(handler, LookupHandler):
            RUNWAY_LOOKUP_HANDLERS[lookup_type] = handler
            return
    except Exception:  # noqa: BLE001
        LOGGER.debug("failed to validate lookup handler", exc_info=True)
    raise TypeError(
        f"lookup {handler_or_path} must be a subclass of "
        "runway.lookups.handlers.base.LookupHandler"
    )


def unregister_lookup_handler(lookup_type: str) -> None:
    """Unregister the specified test type.

    This is useful when testing various lookup types if you want to unregister
    the lookup type after the test runs.

    Args:
        lookup_type: Name of the lookup type to unregister

    """
    RUNWAY_LOOKUP_HANDLERS.pop(lookup_type, None)


register_lookup_handler(CfnLookup.TYPE_NAME, CfnLookup)
register_lookup_handler(EcrLookup.TYPE_NAME, EcrLookup)
register_lookup_handler(EnvLookup.TYPE_NAME, EnvLookup)
register_lookup_handler(RandomStringLookup.TYPE_NAME, RandomStringLookup)
register_lookup_handler(SsmLookup.TYPE_NAME, SsmLookup)
register_lookup_handler(VarLookup.TYPE_NAME, VarLookup)
