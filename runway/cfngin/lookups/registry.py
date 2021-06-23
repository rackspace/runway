"""CFNgin lookup registry."""
from __future__ import annotations

import logging
from typing import Dict, Type, Union, cast

from ...lookups.handlers import cfn, ecr, random_string, ssm
from ...lookups.handlers.base import LookupHandler
from ...utils import DOC_SITE, load_object_from_string
from .handlers import ami, default, dynamodb, envvar
from .handlers import file as file_handler
from .handlers import hook_data, kms, output, rxref, split, xref

CFNGIN_LOOKUP_HANDLERS: Dict[str, Type[LookupHandler]] = {}
LOGGER = logging.getLogger(__name__)


def register_lookup_handler(
    lookup_type: str, handler_or_path: Union[str, Type[LookupHandler]]
) -> None:
    """Register a lookup handler.

    Args:
        lookup_type: Name to register the handler under.
        handler_or_path: A function or a path to a handler.

    """
    handler = handler_or_path
    LOGGER.debug("registering CFNgin lookup: %s=%s", lookup_type, handler_or_path)

    if isinstance(handler_or_path, str):
        handler = cast(type, load_object_from_string(handler_or_path))
    else:
        handler = handler_or_path

    try:
        if issubclass(handler, LookupHandler):
            CFNGIN_LOOKUP_HANDLERS[lookup_type] = handler
            return
    # Hander is a not a new-style handler
    except Exception:  # pylint: disable=broad-except
        LOGGER.debug("failed to validate lookup handler", exc_info=True)
    LOGGER.error(
        'lookup "%s" uses an unsupported format; to learn how to write '
        "lookups visit %s/page/cfngin/lookups.html#writing-a-custom-lookup",
        lookup_type,
        DOC_SITE,
    )
    raise TypeError(
        f"lookup {handler_or_path} must be a subclass of "
        "runway.lookups.handlers.base.LookupHandler"
    )


def unregister_lookup_handler(lookup_type: str) -> None:
    """Unregister the specified lookup type.

    This is useful when testing various lookup types if you want to unregister
    the lookup type after the test runs.

    Args:
        lookup_type: Name of the lookup type to unregister.

    """
    CFNGIN_LOOKUP_HANDLERS.pop(lookup_type, None)


register_lookup_handler(ami.TYPE_NAME, ami.AmiLookup)
register_lookup_handler(cfn.TYPE_NAME, cfn.CfnLookup)
register_lookup_handler(default.TYPE_NAME, default.DefaultLookup)
register_lookup_handler(dynamodb.TYPE_NAME, dynamodb.DynamodbLookup)
register_lookup_handler(ecr.TYPE_NAME, ecr.EcrLookup)
register_lookup_handler(envvar.TYPE_NAME, envvar.EnvvarLookup)
register_lookup_handler(file_handler.TYPE_NAME, file_handler.FileLookup)
register_lookup_handler(hook_data.TYPE_NAME, hook_data.HookDataLookup)
register_lookup_handler(kms.TYPE_NAME, kms.KmsLookup)
register_lookup_handler(output.TYPE_NAME, output.OutputLookup)
register_lookup_handler(random_string.TYPE_NAME, random_string.RandomStringLookup)
register_lookup_handler(rxref.TYPE_NAME, rxref.RxrefLookup)
register_lookup_handler(split.TYPE_NAME, split.SplitLookup)
register_lookup_handler(ssm.TYPE_NAME, ssm.SsmLookup)
register_lookup_handler(xref.TYPE_NAME, xref.XrefLookup)
