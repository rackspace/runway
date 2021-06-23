"""Register test handlers."""
from __future__ import annotations

import logging
from typing import Dict, Type, Union, cast

from ..utils import load_object_from_string
from .handlers import cfn, ecr, env, random_string, ssm, var
from .handlers.base import LookupHandler

RUNWAY_LOOKUP_HANDLERS: Dict[str, Type[LookupHandler]] = {}
LOGGER = logging.getLogger(__name__)


def register_lookup_handler(
    lookup_type: str, handler_or_path: Union[str, Type[LookupHandler]]
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
    except Exception:  # pylint: disable=broad-except
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


register_lookup_handler(cfn.TYPE_NAME, cfn.CfnLookup)
register_lookup_handler(ecr.TYPE_NAME, ecr.EcrLookup)
register_lookup_handler(env.TYPE_NAME, env.EnvLookup)
register_lookup_handler(random_string.TYPE_NAME, random_string.RandomStringLookup)
register_lookup_handler(ssm.TYPE_NAME, ssm.SsmLookup)
register_lookup_handler(var.TYPE_NAME, var.VarLookup)
